"""Firestore 백엔드 로직 테스트.

실제 Firebase에 접속하지 않고, Firestore 클라이언트와 같은 모양의 가짜 객체로
문서 변환·조회·저장 로직을 검증한다.
"""

from datetime import datetime, timedelta, timezone

import pytest

import config
import store


class FakeDocumentSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    def to_dict(self):
        return dict(self._data)


class FakeDocumentReference:
    def __init__(self, collection, doc_id):
        self._collection = collection
        self.id = doc_id

    def set(self, data):
        self._collection.documents[self.id] = dict(data)


class FakeQuery:
    def __init__(self, documents, predicate=None):
        self._documents = documents
        self._predicate = predicate

    def stream(self):
        for doc_id, data in self._documents.items():
            if self._predicate is None or self._predicate(data):
                yield FakeDocumentSnapshot(doc_id, data)

    def limit(self, count):
        limited = dict(list(self._documents.items())[:count])
        return FakeQuery(limited, self._predicate)


class FakeCollection:
    def __init__(self):
        self.documents = {}
        self._counter = 0

    def document(self, doc_id=None):
        if doc_id is None:
            self._counter += 1
            doc_id = f'doc{self._counter}'
        return FakeDocumentReference(self, doc_id)

    def where(self, *args, filter=None):  # noqa: A002 - Firestore SDK 시그니처를 따른다
        if filter is not None:
            field, _, value = filter.field_path, filter.op_string, filter.value
        else:
            field, _, value = args
        return FakeQuery(self.documents, lambda data: data.get(field) == value)

    def limit(self, count):
        return FakeQuery(self.documents).limit(count)

    def stream(self):
        return FakeQuery(self.documents).stream()


@pytest.fixture
def firestore_store():
    """FirestoreStore를 실제 초기화 없이 가짜 컬렉션에 연결한다."""
    instance = store.FirestoreStore.__new__(store.FirestoreStore)
    store.RecordStore.__init__(instance, cache_ttl_seconds=0)
    collection = FakeCollection()
    # _collection 프로퍼티를 가짜 컬렉션으로 대체한다.
    instance.__class__ = type('TestFirestoreStore', (store.FirestoreStore,),
                              {'_collection': property(lambda self: collection)})
    instance.fake_collection = collection
    return instance


def test_field_filter_is_available():
    """설치된 SDK에서 FieldFilter를 쓸 수 있어야 한다(구버전 fallback 확인용)."""
    from google.cloud.firestore_v1.base_query import FieldFilter

    assert FieldFilter('mode', '==', '자리') is not None


def test_add_and_fetch_roundtrip(firestore_store):
    created_at = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    saved = firestore_store.add(student_id='10218 홍길동', mode='자리', wpm=200,
                                accuracy=95.0, score=18050, duration_sec=300,
                                created_at=created_at)

    assert saved['id'] == 'doc1'
    # 문서에는 id를 중복 저장하지 않는다.
    assert set(firestore_store.fake_collection.documents['doc1']) == set(store.RECORD_FIELDS)

    records = firestore_store.top('자리')
    assert len(records) == 1
    assert records[0]['student_id'] == '10218 홍길동'
    assert records[0]['created_at'] == created_at


def test_mode_filter_excludes_other_modes(firestore_store):
    firestore_store.add(student_id='10101 가나다', mode='자리', wpm=100, accuracy=90.0,
                        score=8100, duration_sec=300)
    firestore_store.add(student_id='10102 라마바', mode='낱말', wpm=100, accuracy=90.0,
                        score=8100, duration_sec=300)

    assert len(firestore_store.top('자리')) == 1
    assert len(firestore_store.top('낱말')) == 1
    assert firestore_store.stats()['total_records'] == 2


def test_sorting_applied_to_firestore_results(firestore_store):
    now = datetime.now(timezone.utc)
    for index, score in enumerate([100, 500, 300]):
        firestore_store.add(student_id=f'102{index:02d} 홍길동', mode='자리', wpm=100,
                            accuracy=90.0, score=score, duration_sec=300,
                            created_at=now + timedelta(seconds=index))

    assert [r['score'] for r in firestore_store.top('자리')] == [500, 300, 100]


def test_naive_and_string_timestamps_are_normalized(firestore_store):
    firestore_store.fake_collection.documents['legacy_naive'] = {
        'student_id': '10301 가나다', 'mode': '자리', 'wpm': 100, 'accuracy': 90.0,
        'score': 8100, 'duration_sec': 300,
        # Firestore 이전 데이터가 timezone 정보 없이 들어온 경우
        'created_at': datetime(2026, 1, 1, 0, 0),
    }
    firestore_store.fake_collection.documents['legacy_string'] = {
        'student_id': '10302 라마바', 'mode': '자리', 'wpm': 100, 'accuracy': 90.0,
        'score': 8100, 'duration_sec': 300,
        'created_at': '2026-01-02T00:00:00Z',
    }

    records = {r['id']: r for r in firestore_store.top('자리')}
    assert records['legacy_naive']['created_at'].tzinfo is not None
    assert records['legacy_string']['created_at'].tzinfo is not None
    # 정렬이 깨지지 않아야 한다(비교 가능한 datetime).
    assert len(firestore_store.top('자리')) == 2


def test_missing_fields_do_not_crash(firestore_store):
    firestore_store.fake_collection.documents['broken'] = {'mode': '자리'}

    records = firestore_store.top('자리')
    assert records[0]['wpm'] == 0
    assert records[0]['student_id'] == ''
    assert store.to_api_dict(records[0])['created_at'] is None


def test_ping_uses_limit_query(firestore_store):
    assert firestore_store.ping() is True


def test_cache_reduces_reads():
    """캐시를 켜면 같은 모드를 연속 조회할 때 Firestore를 다시 읽지 않는다."""
    instance = store.FirestoreStore.__new__(store.FirestoreStore)
    store.RecordStore.__init__(instance, cache_ttl_seconds=60)
    calls = []

    def fetch(mode):
        calls.append(mode)
        return []

    instance._fetch_mode = fetch

    instance.records_for_mode('자리')
    instance.records_for_mode('자리')
    assert calls == ['자리']

    instance.invalidate('자리')
    instance.records_for_mode('자리')
    assert calls == ['자리', '자리']


def test_create_store_without_credentials_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'STORE_BACKEND', 'auto')
    monkeypatch.setattr(config, 'LOCAL_DB_PATH', str(tmp_path / 'records.json'))
    for name in ('FIREBASE_SERVICE_ACCOUNT_JSON', 'FIREBASE_SERVICE_ACCOUNT_FILE',
                 'GOOGLE_APPLICATION_CREDENTIALS'):
        monkeypatch.delenv(name, raising=False)

    assert store.firebase_credentials_available() is False
    assert store.create_store().backend == 'local'


def test_create_store_prefers_firestore_when_credentials_exist(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'STORE_BACKEND', 'auto')
    monkeypatch.setattr(config, 'LOCAL_DB_PATH', str(tmp_path / 'records.json'))
    monkeypatch.setenv('FIREBASE_SERVICE_ACCOUNT_JSON', '{"type": "service_account"}')

    created = []
    monkeypatch.setattr(store, '_create_firestore_client',
                        lambda: created.append('client') or object())

    assert store.create_store().backend == 'firestore'
    assert created == ['client']


def test_create_store_falls_back_when_firestore_init_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'STORE_BACKEND', 'auto')
    monkeypatch.setattr(config, 'LOCAL_DB_PATH', str(tmp_path / 'records.json'))
    monkeypatch.setenv('FIREBASE_SERVICE_ACCOUNT_JSON', '{"type": "service_account"}')

    def boom():
        raise RuntimeError('자격 증명이 잘못되었습니다')

    monkeypatch.setattr(store, '_create_firestore_client', boom)

    # 자격 증명이 잘못되어도 앱이 뜨지 않는 일은 없어야 한다.
    assert store.create_store().backend == 'local'
