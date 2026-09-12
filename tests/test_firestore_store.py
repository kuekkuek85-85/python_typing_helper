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


class FakeAggregationResult:
    def __init__(self, value):
        self.value = value


class FakeQuery:
    """Firestore Query 흉내. order_by 지원 여부를 테스트에서 바꿀 수 있다."""

    def __init__(self, documents, predicate=None, supports_order_by=True,
                 order_specs=(), limit_count=None, reads=None):
        self._documents = documents
        self._predicate = predicate
        self._supports_order_by = supports_order_by
        # (필드, 내림차순여부) 목록. Firestore처럼 연쇄 order_by를 누적한다.
        self._order_specs = tuple(order_specs)
        self._limit = limit_count
        # 읽은 문서 수를 기록해 "전체를 읽지 않는다"를 검증한다.
        self.reads = reads if reads is not None else []

    def _clone(self, **overrides):
        params = dict(documents=self._documents, predicate=self._predicate,
                      supports_order_by=self._supports_order_by,
                      order_specs=self._order_specs,
                      limit_count=self._limit, reads=self.reads)
        params.update(overrides)
        return FakeQuery(**params)

    def _matching(self):
        items = [(doc_id, data) for doc_id, data in self._documents.items()
                 if self._predicate is None or self._predicate(data)]

        # 정렬 기준이 없으면 Firestore는 문서 ID 순으로 돌려준다.
        items.sort(key=lambda item: item[0])
        # 뒤쪽 기준부터 차례로 안정 정렬하면 다중 정렬과 같은 결과가 된다.
        for field, descending in reversed(self._order_specs):
            items.sort(key=lambda item: item[1].get(field, 0), reverse=descending)

        if self._limit is not None:
            items = items[:self._limit]
        return items

    def stream(self):
        items = self._matching()
        self.reads.append(len(items))
        for doc_id, data in items:
            yield FakeDocumentSnapshot(doc_id, data)

    def order_by(self, field, direction=None):
        if not self._supports_order_by:
            # 실제 Firestore는 복합 색인이 없으면 FAILED_PRECONDITION을 던진다.
            raise RuntimeError('The query requires an index.')
        spec = (field, direction == 'DESCENDING')
        return self._clone(order_specs=self._order_specs + (spec,))

    def limit(self, count):
        return self._clone(limit_count=count)

    def count(self, alias=None):
        return FakeAggregationQuery(self)


class FakeAggregationQuery:
    def __init__(self, query):
        self._query = query

    def get(self):
        total = len(self._query._matching())
        # 집계 쿼리는 문서를 읽지 않는다(읽기 기록을 남기지 않음).
        return [[FakeAggregationResult(total)]]


class FakeCollection:
    def __init__(self, supports_order_by=True):
        self.documents = {}
        self.supports_order_by = supports_order_by
        self.reads = []
        self._counter = 0

    @property
    def documents_read(self) -> int:
        return sum(self.reads)

    def document(self, doc_id=None):
        if doc_id is None:
            self._counter += 1
            doc_id = f'doc{self._counter}'
        return FakeDocumentReference(self, doc_id)

    def _query(self, predicate=None):
        return FakeQuery(self.documents, predicate,
                         supports_order_by=self.supports_order_by, reads=self.reads)

    def where(self, *args, filter=None):  # noqa: A002 - Firestore SDK 시그니처를 따른다
        if filter is not None:
            field, _, value = filter.field_path, filter.op_string, filter.value
        else:
            field, _, value = args
        return self._query(lambda data: data.get(field) == value)

    def limit(self, count):
        return self._query().limit(count)

    def stream(self):
        return self._query().stream()


def _make_store(collection, cache_ttl_seconds=0):
    """FirestoreStore를 실제 초기화 없이 가짜 컬렉션에 연결한다."""
    instance = store.FirestoreStore.__new__(store.FirestoreStore)
    store.RecordStore.__init__(instance, cache_ttl_seconds=cache_ttl_seconds)
    instance._head_fetch_warned = False
    instance.__class__ = type('TestFirestoreStore', (store.FirestoreStore,),
                              {'_collection': property(lambda self: collection)})
    instance.fake_collection = collection
    return instance


@pytest.fixture
def firestore_store():
    return _make_store(FakeCollection())


@pytest.fixture
def firestore_store_without_index():
    """복합 색인이 없는 프로젝트(order_by 실패)를 흉내 낸다."""
    return _make_store(FakeCollection(supports_order_by=False))


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


# --- 읽는 문서 수 제한 (Codex P1: Firestore 조회를 서버 측에서 제한) ---------
def _seed(record_store, count, mode='자리'):
    for index in range(count):
        record_store.add(student_id=f'1{index:04d} 홍길동', mode=mode, wpm=100,
                         accuracy=90.0, score=index, duration_sec=300)
    record_store.fake_collection.reads.clear()
    record_store.invalidate()


def test_count_for_mode_uses_aggregation_without_reading_documents(firestore_store):
    _seed(firestore_store, 50)

    assert firestore_store.count_for_mode('자리') == 50
    # 집계 쿼리이므로 문서를 한 건도 읽지 않아야 한다.
    assert firestore_store.fake_collection.documents_read == 0


def test_top_reads_only_head_documents(firestore_store):
    _seed(firestore_store, 300)

    top = firestore_store.top('자리', 10)

    assert [record['score'] for record in top] == list(range(299, 289, -1))
    read = firestore_store.fake_collection.documents_read
    assert 0 < read <= store.HEAD_FETCH_MAX, read
    # 전체(300건)를 읽지 않는다.
    assert read < 300


def test_page_total_does_not_read_all_documents(firestore_store):
    _seed(firestore_store, 300)

    records, total = firestore_store.page('자리', limit=1, offset=0)

    assert total == 300
    assert len(records) == 1
    assert firestore_store.fake_collection.documents_read < 300


def test_full_view_still_returns_every_record(firestore_store):
    _seed(firestore_store, 300)

    records, total = firestore_store.page('자리', limit=2000, offset=0)

    assert total == 300
    assert len(records) == 300


def test_falls_back_to_full_read_without_composite_index(firestore_store_without_index):
    _seed(firestore_store_without_index, 30)

    top = firestore_store_without_index.top('자리', 10)

    # 색인이 없어도 결과는 동일해야 한다(앱이 그대로 동작).
    assert [record['score'] for record in top] == list(range(29, 19, -1))
    assert firestore_store_without_index._head_fetch_warned is True


def test_head_and_full_read_agree_on_ordering(firestore_store, firestore_store_without_index):
    """색인이 있을 때와 없을 때 순위가 같아야 한다(동점자 포함)."""
    for record_store in (firestore_store, firestore_store_without_index):
        for index in range(40):
            record_store.add(student_id=f'2{index:04d} 김영희', mode='자리', wpm=100 + index % 3,
                             accuracy=90.0, score=500 if index < 15 else index,
                             duration_sec=300)
        record_store.invalidate()

    with_index = [r['student_id'] for r in firestore_store.top('자리', 10)]
    without_index = [r['student_id'] for r in firestore_store_without_index.top('자리', 10)]
    assert with_index == without_index


def test_cache_invalidated_for_derived_keys(firestore_store):
    record_store = _make_store(firestore_store.fake_collection, cache_ttl_seconds=60)
    _seed(record_store, 5)

    assert record_store.count_for_mode('자리') == 5
    record_store.add(student_id='19999 새기록', mode='자리', wpm=100, accuracy=90.0,
                     score=999, duration_sec=300)
    # add()가 파생 캐시(count/head)까지 비워야 새 기록이 보인다.
    assert record_store.count_for_mode('자리') == 6
    assert record_store.top('자리', 1)[0]['student_id'] == '19999 새기록'


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


# --- 색인 선언과 정렬 기준 일치 -------------------------------------------
def test_declared_index_matches_sort_order():
    """firestore.indexes.json 과 store.SORT_ORDER 가 어긋나지 않게 고정한다.

    색인 경로는 SORT_ORDER 전부를 Firestore order_by 에 넣는다. 선언된 색인이
    그와 다르면 색인이 쿼리를 서비스하지 못해 항상 전체 읽기로 대체되거나,
    동점자 처리가 밀려 전체 읽기 경로와 순위가 달라진다.
    """
    import json
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'firestore.indexes.json')
    with open(path, encoding='utf-8') as handle:
        indexes = json.load(handle)['indexes']

    assert len(indexes) == 1, '색인 선언이 하나여야 한다'
    declared = [(field['fieldPath'], field['order']) for field in indexes[0]['fields']]

    # 첫 필드는 모드 등호 필터, 그 뒤는 정렬 기준 순서와 같아야 한다.
    expected = [('mode', 'ASCENDING')] + list(store.SORT_ORDER)
    assert declared == expected, f'선언={declared} 기대={expected}'
    assert indexes[0]['collectionGroup'] == config.FIRESTORE_COLLECTION


# --- 동점자 처리 (Codex P1: 모든 동점 정렬 키를 쿼리에 포함) ----------------
def test_head_path_orders_by_every_sort_key(firestore_store):
    """쿼리가 정렬 기준 전부를 order_by 에 넣는지 확인한다."""
    firestore_store.add(student_id='10001 가나다', mode='자리', wpm=100, accuracy=90.0,
                        score=500, duration_sec=300)
    firestore_store.top('자리', 1)

    query = _apply_mode(firestore_store.fake_collection, '자리')
    for field, direction in store.SORT_ORDER:
        query = query.order_by(field, direction=direction)
    assert query._order_specs == tuple(
        (field, direction == 'DESCENDING') for field, direction in store.SORT_ORDER)


def _apply_mode(collection, mode):
    from google.cloud.firestore_v1.base_query import FieldFilter

    return collection.where(filter=FieldFilter('mode', '==', mode))


def test_ties_beyond_any_buffer_still_rank_correctly(firestore_store,
                                                     firestore_store_without_index):
    """읽어오는 개수보다 동점자가 많아도 Top10이 정확해야 한다.

    이전 구현은 score만 정렬해 상위 50건을 읽은 뒤 나머지 기준을 파이썬에서
    적용했다. 같은 점수가 50건을 넘으면 경계에서 더 높은 정확도·타수의 기록이
    잘려 색인 경로와 전체 읽기 경로의 순위가 달라졌다.
    """
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # 같은 점수 300건. 정확도는 뒤에 만든 기록이 더 높게 만든다.
    for index in range(300):
        for record_store in (firestore_store, firestore_store_without_index):
            record_store.add(student_id=f'3{index:04d} 김영희', mode='자리',
                             wpm=100, accuracy=50.0 + index * 0.1,
                             score=9999, duration_sec=300,
                             created_at=base + timedelta(seconds=index))
    for record_store in (firestore_store, firestore_store_without_index):
        record_store.invalidate()

    with_index = [r['student_id'] for r in firestore_store.top('자리', 10)]
    without_index = [r['student_id'] for r in firestore_store_without_index.top('자리', 10)]

    # 정확도가 가장 높은 10명(마지막에 만든 기록들)이 나와야 한다.
    expected = [f'3{index:04d} 김영희' for index in range(299, 289, -1)]
    assert with_index == expected, with_index
    # 색인 유무와 무관하게 순위가 같아야 한다.
    assert with_index == without_index


def test_ties_on_score_and_accuracy_fall_through_to_wpm(firestore_store):
    base = datetime(2026, 2, 1, tzinfo=timezone.utc)
    for index in range(120):
        firestore_store.add(student_id=f'4{index:04d} 박철수', mode='자리',
                            wpm=index, accuracy=88.0, score=7000, duration_sec=300,
                            created_at=base + timedelta(seconds=index))
    firestore_store.invalidate()

    top = firestore_store.top('자리', 5)
    assert [r['wpm'] for r in top] == [119, 118, 117, 116, 115]


# --- 캐시 경쟁 조건 (Codex P2: 무효화 이후 오래된 캐시 재저장 방지) ---------
def test_stale_list_is_not_cached_after_invalidation(firestore_store):
    """조회 도중 새 기록이 저장되면 옛 목록을 캐시하지 않아야 한다."""
    record_store = _make_store(firestore_store.fake_collection, cache_ttl_seconds=60)
    record_store.add(student_id='50001 가나다', mode='자리', wpm=100, accuracy=90.0,
                     score=100, duration_sec=300)

    original_fetch = record_store._fetch_mode

    def fetch_then_someone_else_saves(mode):
        records = original_fetch(mode)
        # 이 조회가 진행되는 동안 다른 스레드가 기록을 저장했다고 가정한다.
        record_store.add(student_id='50002 라마바', mode='자리', wpm=100,
                         accuracy=95.0, score=900, duration_sec=300)
        return records

    record_store._fetch_mode = fetch_then_someone_else_saves
    stale = record_store.records_for_mode('자리')
    assert len(stale) == 1, '이번 조회 자체는 옛 데이터를 볼 수 있다'

    # 하지만 그 결과가 캐시에 남아서는 안 된다.
    record_store._fetch_mode = original_fetch
    assert len(record_store.records_for_mode('자리')) == 2, '새 기록이 바로 보여야 한다'


def test_store_cache_rejects_value_from_older_generation(firestore_store):
    """무효화 세대 확인이 실제로 동작하는지 직접 검증한다.

    count/head/목록 캐시가 모두 같은 _store_cache 경로를 쓰므로,
    이 확인이 곧 모든 캐시 종류에 적용된다.
    """
    record_store = _make_store(firestore_store.fake_collection, cache_ttl_seconds=60)

    generation = record_store._generation('자리')   # 조회 시작
    record_store.invalidate('자리')                 # 조회 도중 다른 스레드가 저장
    record_store._store_cache('자리', ['오래된 값'], mode='자리', generation=generation)

    assert record_store._cached('자리') is None, '무효화된 세대의 값은 캐시되면 안 된다'


def test_store_cache_accepts_value_from_current_generation(firestore_store):
    record_store = _make_store(firestore_store.fake_collection, cache_ttl_seconds=60)

    generation = record_store._generation('자리')
    record_store._store_cache('자리', ['최신 값'], mode='자리', generation=generation)

    assert record_store._cached('자리') == ['최신 값']


def test_invalidate_all_also_bumps_generation(firestore_store):
    record_store = _make_store(firestore_store.fake_collection, cache_ttl_seconds=60)

    generation = record_store._generation('자리')
    record_store.invalidate()   # 전체 무효화
    record_store._store_cache('자리', ['오래된 값'], mode='자리', generation=generation)

    assert record_store._cached('자리') is None
