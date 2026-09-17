"""Firestore 연습 세션·빈도 제한 백엔드 테스트.

여기서 확인하려는 것은 하나다. **요청마다 프로세스가 달라져도 연습이 이어지는가.**
서버리스(Vercel)에서는 키 입력을 받은 인스턴스와 기록을 저장하는 인스턴스가
다를 수 있는데, 프로세스 메모리에 세션을 두면 그때 "타이핑 세션을 찾을 수
없습니다"가 난다.

테스트 더블은 Firestore의 **격리(isolation)까지 흉내 내지는 않는다.** 진짜
트랜잭션이 동시 쓰기를 어떻게 직렬화하는지는 로컬에서 검증할 수 없다. 여기서
고정하는 것은 읽고-고쳐-쓰는 로직과 문서 모양이다.
"""

from datetime import datetime, timezone

import pytest

import config
import sessions
import store
from app import create_app


# --- 테스트 더블 ----------------------------------------------------------
class FakeSnapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class FakeDocumentReference:
    def __init__(self, collection, doc_id):
        self._collection = collection
        self.id = doc_id

    def get(self, transaction=None):
        self._collection.reads += 1
        return FakeSnapshot(self._collection.docs.get(self.id))

    def set(self, data):
        self._collection.writes += 1
        self._collection.docs[self.id] = dict(data)

    def delete(self):
        self._collection.deletes += 1
        self._collection.docs.pop(self.id, None)


class FakeTransaction:
    """set()을 즉시 적용한다(격리는 흉내 내지 않는다)."""

    def set(self, doc_ref, data):
        doc_ref.set(data)


class FakeCollection:
    def __init__(self):
        self.docs = {}
        self.reads = 0
        self.writes = 0
        self.deletes = 0

    def document(self, doc_id):
        return FakeDocumentReference(self, doc_id)


class FakeClient:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        return self.collections.setdefault(name, FakeCollection())

    def transaction(self):
        return FakeTransaction()


def _identity(func):
    """@firestore.transactional 자리에 끼우는 통과 데코레이터."""
    return func


@pytest.fixture
def fake_client():
    return FakeClient()


@pytest.fixture
def limiter(fake_client):
    return sessions.FirestoreRateLimiter(client=fake_client, transactional=_identity)


@pytest.fixture
def registry(fake_client):
    return sessions.FirestoreSessionRegistry(client=fake_client, transactional=_identity)


def _new_registry(fake_client):
    """같은 Firestore를 보는 **다른 인스턴스**를 흉내 낸다."""
    return sessions.FirestoreSessionRegistry(client=fake_client, transactional=_identity)


# --- 핵심: 인스턴스가 달라져도 연습이 이어진다 ----------------------------
def test_practice_survives_across_instances(fake_client):
    """각 단계를 전부 다른 인스턴스가 처리해도 키 입력이 누적된다."""
    _new_registry(fake_client).create('sess-1')
    _new_registry(fake_client).start('sess-1')

    for _ in range(4):
        _new_registry(fake_client).add_keystrokes('sess-1', 10)

    activity = _new_registry(fake_client).get('sess-1')
    assert activity is not None
    assert activity.count == 40
    assert activity.started_at is not None


def test_memory_backend_loses_the_session_across_instances():
    """대조군. 메모리 백엔드가 왜 서버리스에서 안 되는지 고정해 둔다."""
    sessions.TypingSessionRegistry().create('sess-1')
    assert sessions.TypingSessionRegistry().get('sess-1') is None


def test_unknown_session_returns_none(registry):
    assert registry.get('없는-세션') is None
    assert registry.start('없는-세션') is None
    assert registry.add_keystrokes('없는-세션', 10) is None


def test_keystrokes_before_start_are_ignored(registry):
    registry.create('sess-2')
    assert registry.add_keystrokes('sess-2', 10) is None

    activity = registry.get('sess-2')
    assert activity.count == 0


def test_discard_removes_the_document(registry, fake_client):
    registry.create('sess-3')
    collection = fake_client.collection(config.FIRESTORE_SESSION_COLLECTION)
    assert len(collection.docs) == 1

    registry.discard('sess-3')
    assert collection.docs == {}
    assert registry.get('sess-3') is None


def test_discard_failure_does_not_raise(registry, monkeypatch):
    """세션 정리에 실패해도 기록 저장 경로를 막으면 안 된다."""
    registry.create('sess-4')

    def boom():
        raise RuntimeError('Firestore 연결 끊김')

    monkeypatch.setattr(FakeDocumentReference, 'delete', lambda self: boom())
    registry.discard('sess-4')  # 예외가 밖으로 나오지 않는다


# --- 트랜잭션 실패 (실제 Firestore에서 재현됐다) --------------------------
#
# 같은 문서에 요청 10개를 동시에 보내면 Firestore가 재시도를 소진하고
# "Failed to commit transaction in N attempts"를 던진다. 연습 중에 이게 500으로
# 올라오면, 세션은 멀쩡한데 학생 화면에만 오류가 뜬다.
def _exploding_transactional(func):
    def boom(*args, **kwargs):
        raise ValueError('Failed to commit transaction in 5 attempts.')

    return boom


def test_keystroke_report_is_dropped_not_raised(fake_client):
    """보고 실패는 이번 묶음만 버리고, 현재 상태를 그대로 돌려준다."""
    healthy = sessions.FirestoreSessionRegistry(client=fake_client, transactional=_identity)
    healthy.create('sess-10')
    healthy.start('sess-10')
    healthy.add_keystrokes('sess-10', 40)

    failing = sessions.FirestoreSessionRegistry(
        client=fake_client, transactional=_exploding_transactional)
    activity = failing.add_keystrokes('sess-10', 40)

    # None이면 라우트가 409 "연습이 시작되지 않았습니다"를 내보낸다 — 사실과 다르다.
    assert activity is not None
    assert activity.count == 40, '실패한 묶음은 반영되지 않는다'


def test_keystroke_route_stays_200_when_transaction_fails(record_store, fake_client):
    """연습 중 Firestore가 흔들려도 화면에 오류가 뜨지 않아야 한다."""
    app = create_app(
        record_store=record_store,
        typing_sessions=sessions.FirestoreSessionRegistry(
            client=fake_client, transactional=_identity),
        rate_limiter=sessions.FirestoreRateLimiter(
            client=fake_client, transactional=_identity),
    )
    app.config.update(TESTING=True)
    client = app.test_client()

    client.get('/practice/자리')
    with client.session_transaction() as flask_session:
        token = flask_session['practice']['token']
    client.post('/api/practice/start', json={'practice_token': token})

    app.extensions['typing_sessions']._transactional = _exploding_transactional
    response = client.post('/api/keystroke', json={'count': 20, 'practice_token': token})

    assert response.status_code == 200, response.get_json()


def test_start_failure_asks_the_student_to_retry(fake_client):
    """시작 기록은 버리면 안 된다. None을 돌려 라우트가 409로 안내하게 한다."""
    healthy = sessions.FirestoreSessionRegistry(client=fake_client, transactional=_identity)
    healthy.create('sess-11')

    failing = sessions.FirestoreSessionRegistry(
        client=fake_client, transactional=_exploding_transactional)
    assert failing.start('sess-11') is None


def test_transaction_asks_for_more_attempts_than_the_sdk_default(fake_client, monkeypatch):
    """재시도 횟수를 늘려 경합에 버티게 한다(SDK 기본값은 5)."""
    requested = {}

    def transaction(max_attempts=None):
        requested['max_attempts'] = max_attempts
        return FakeTransaction()

    monkeypatch.setattr(fake_client, 'transaction', transaction)
    registry = sessions.FirestoreSessionRegistry(client=fake_client, transactional=_identity)
    registry.create('sess-12')
    registry.start('sess-12')

    assert requested['max_attempts'] == config.FIRESTORE_MAX_ATTEMPTS
    assert config.FIRESTORE_MAX_ATTEMPTS > 5


def test_old_sdk_without_max_attempts_still_works(fake_client, monkeypatch):
    def transaction_without_kwarg():
        return FakeTransaction()

    monkeypatch.setattr(fake_client, 'transaction', transaction_without_kwarg)
    registry = sessions.FirestoreSessionRegistry(client=fake_client, transactional=_identity)
    registry.create('sess-13')

    assert registry.start('sess-13') is not None


# --- 부정행위 방지가 백엔드에 따라 달라지지 않는다 ------------------------
def test_inflated_report_is_still_capped(registry):
    """개수를 부풀려도 토큰 버킷이 깎는다(메모리 백엔드와 같은 규칙)."""
    registry.create('sess-5')
    registry.start('sess-5')
    registry.add_keystrokes('sess-5', 6000)

    activity = registry.get('sess-5')
    assert activity.reported_count == 6000
    # 시작 직후 버킷에 있는 양(KEYSTROKE_BURST) 언저리까지만 인정된다.
    assert config.KEYSTROKE_BURST <= activity.count <= config.KEYSTROKE_BURST + 20


def test_both_backends_agree_on_the_same_sequence(fake_client):
    """같은 입력 순서에 두 백엔드가 같은 집계를 낸다."""
    memory = sessions.TypingSessionRegistry()
    firestore = sessions.FirestoreSessionRegistry(client=fake_client, transactional=_identity)

    for registry in (memory, firestore):
        registry.create('sess-6')
        registry.start('sess-6')
        for _ in range(5):
            registry.add_keystrokes('sess-6', 12)

    assert memory.get('sess-6').count == firestore.get('sess-6').count == 60


# --- 문서 모양 ------------------------------------------------------------
def test_document_round_trip_preserves_state(registry, fake_client):
    registry.create('sess-7')
    registry.start('sess-7')
    registry.add_keystrokes('sess-7', 25)

    collection = fake_client.collection(config.FIRESTORE_SESSION_COLLECTION)
    stored = collection.docs[sessions._session_doc_id('sess-7')]

    restored = sessions.TypingActivity.from_dict(stored)
    assert restored.count == 25
    assert restored.reported_count == 25
    assert restored.started_at is not None
    assert restored.first_keystroke_at is not None


def test_expires_at_is_a_timestamp_not_a_number(registry, fake_client, limiter):
    """TTL 정책은 **타임스탬프 타입 필드만** 만료 대상으로 본다.

    Unix 초(float)로 쓰면 정책을 걸어 두어도 아무것도 지워지지 않고, 버려진 세션
    문서가 영원히 쌓인다. 안내한 대로 따랐는데 동작하지 않는 쪽이 더 나쁘다.
    """
    registry.create('sess-8')
    registry.start('sess-8')
    limiter.allow('10101 가나다')

    now = datetime.now(timezone.utc)
    checked = 0
    for name in (config.FIRESTORE_SESSION_COLLECTION, config.FIRESTORE_RATE_LIMIT_COLLECTION):
        for stored in fake_client.collection(name).docs.values():
            expires_at = stored['expires_at']
            assert isinstance(expires_at, datetime), f'{name}: {type(expires_at)}'
            assert expires_at.tzinfo is not None, f'{name}: 시간대가 없으면 해석이 갈린다'
            assert expires_at > now
            checked += 1

    assert checked == 2, '두 컬렉션 모두 확인해야 한다'


def test_from_dict_tolerates_missing_and_broken_fields():
    """문서가 깨져 있어도 500이 아니라 '세션 없음'으로 흘러가야 한다."""
    activity = sessions.TypingActivity.from_dict({'count': 'abc', 'tokens': None})
    assert activity.count == 0
    assert activity.tokens == 0.0
    assert activity.started_at is None

    assert sessions.TypingActivity.from_dict({}).count == 0


def test_session_document_id_cannot_be_reserved():
    """Firestore는 __...__ 형태의 문서 ID를 예약해 두었다."""
    assert sessions._session_doc_id('__foo__') == 's___foo__'
    assert not sessions._session_doc_id('__foo__').startswith('__')


# --- 쓰기 횟수 (비용) -----------------------------------------------------
def test_write_count_for_one_practice_is_bounded(fake_client):
    """5분 연습 한 번의 Firestore 쓰기 횟수를 고정한다.

    이 숫자가 늘면 무료 한도(하루 쓰기 2만 회)가 그만큼 빨리 소진된다.
    KEYSTROKE_FLUSH_MS를 줄이면 여기가 먼저 깨진다.

    **연습 세션 컬렉션만 세면 안 된다.** 저장이 성공하면 빈도 제한 문서 갱신과
    기록 추가도 각각 과금되는 쓰기다. 여기서는 fake_client의 모든 컬렉션을 센다.
    """
    registry = _new_registry(fake_client)
    limiter = sessions.FirestoreRateLimiter(client=fake_client, transactional=_identity)
    reports = config.PRACTICE_SECONDS // (config.KEYSTROKE_FLUSH_MS // 1000)

    registry.create('sess-9')
    registry.start('sess-9')
    for _ in range(reports):
        registry.add_keystrokes('sess-9', 10)
    limiter.allow('10101 가나다')     # 저장 직전 빈도 제한
    registry.discard('sess-9')        # 저장 후 세션 폐기

    writes = sum(c.writes for c in fake_client.collections.values())
    deletes = sum(c.deletes for c in fake_client.collections.values())

    # 세션 create 1 + start 1 + 보고 30 + 빈도 제한 1 = 33, 그리고 기록 저장 1
    # (records 컬렉션은 store.py가 쓰므로 이 더블에는 잡히지 않는다)
    assert writes == reports + 3
    assert deletes == 1

    total = writes + deletes + 1   # +1 = store.add()의 기록 저장
    assert total <= 40, (
        f'학생 한 명당 {total}회. 40회를 넘으면 DEPLOYMENT.md의 비용 계산을 다시 해야 한다')


# --- 제출 빈도 제한 -------------------------------------------------------
def test_rate_limit_is_shared_across_instances(fake_client):
    def limiter_instance():
        return sessions.FirestoreRateLimiter(client=fake_client, transactional=_identity)

    allowed = [limiter_instance().allow('10101 가나다')
               for _ in range(config.MAX_SUBMISSIONS_PER_WINDOW + 1)]

    assert allowed[:-1] == [True] * config.MAX_SUBMISSIONS_PER_WINDOW
    assert allowed[-1] is False


def test_rate_limit_is_per_student(limiter):
    for _ in range(config.MAX_SUBMISSIONS_PER_WINDOW):
        assert limiter.allow('10101 가나다') is True

    assert limiter.allow('10101 가나다') is False
    assert limiter.allow('10102 라마바') is True


def test_rate_limit_window_expires(fake_client):
    """창을 벗어난 기록은 한도 계산에서 빠진다."""
    collection = fake_client.collection('rate_limits')
    doc_ref = collection.document('student')
    transaction = FakeTransaction()

    assert sessions._allow_within_window(transaction, doc_ref, 1000.0, 300.0, 2) is True
    assert sessions._allow_within_window(transaction, doc_ref, 1001.0, 300.0, 2) is True
    assert sessions._allow_within_window(transaction, doc_ref, 1002.0, 300.0, 2) is False

    # 창(300초)을 넘긴 뒤에는 다시 허용된다.
    assert sessions._allow_within_window(transaction, doc_ref, 1400.0, 300.0, 2) is True


def test_rate_limiter_allows_when_firestore_fails(fake_client, monkeypatch):
    """빈도 제한은 보조 장치다. Firestore가 흔들린다고 정상 저장을 막지 않는다."""
    limiter = sessions.FirestoreRateLimiter(client=fake_client, transactional=_identity)

    def boom(*args, **kwargs):
        raise RuntimeError('Firestore 연결 끊김')

    monkeypatch.setattr(FakeDocumentReference, 'get', boom)
    assert limiter.allow('10101 가나다') is True


def test_rate_limit_document_id_does_not_leak_student_name():
    """학생 이름이 기록 컬렉션 밖으로 더 퍼지지 않게 해싱한다."""
    doc_id = sessions._rate_limit_doc_id('10101 가나다')
    assert '가나다' not in doc_id
    assert '10101' not in doc_id
    assert doc_id == sessions._rate_limit_doc_id('10101 가나다')
    assert doc_id != sessions._rate_limit_doc_id('10102 라마바')


# --- 백엔드 선택 ----------------------------------------------------------
def test_auto_picks_firestore_on_serverless(monkeypatch):
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'auto')
    monkeypatch.setattr(config, 'SERVERLESS', True)
    monkeypatch.setattr(store, 'firebase_credentials_available', lambda: True)
    assert sessions._resolve_backend() == 'firestore'


def test_auto_does_not_pick_firestore_without_credentials(monkeypatch):
    """서버리스 + 자격 증명 없음 → 앱이 **떠야** 한다.

    firestore를 고르면 클라이언트를 만들다 임포트 중에 죽는다. 서버리스에서는
    그게 배포 실패로만 보이고 원인을 알 수 없다. 메모리로 떠서 /health가 무엇이
    잘못됐는지 말하게 하는 편이 낫다. (Vercel 첫 배포가 이것 때문에 실패했다.)
    """
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'auto')
    monkeypatch.setattr(config, 'SERVERLESS', True)
    monkeypatch.setattr(store, 'firebase_credentials_available', lambda: False)
    monkeypatch.setattr(sessions, '_serverless_without_credentials_warned', False)

    assert sessions._resolve_backend() == 'memory'


def test_app_boots_on_serverless_without_credentials(monkeypatch):
    """임포트만으로 죽지 않는지 실제 앱으로 확인한다."""
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'auto')
    monkeypatch.setattr(config, 'SERVERLESS', True)
    monkeypatch.setattr(store, 'firebase_credentials_available', lambda: False)

    app = create_app(record_store=store.LocalJsonStore(path='/dev/null'))
    app.config.update(TESTING=True)

    payload = app.test_client().get('/health').get_json()
    assert payload['session_backend'] == 'memory'


def test_firestore_client_failure_names_the_fix(monkeypatch):
    """배포 로그에서 원인을 찾을 수 있어야 한다."""
    def boom():
        raise RuntimeError('Your default credentials were not found.')

    monkeypatch.setattr(store, 'create_firestore_client', boom)

    with pytest.raises(RuntimeError, match='FIREBASE_SERVICE_ACCOUNT_JSON'):
        sessions._firestore_client()


def test_auto_picks_memory_on_normal_server(monkeypatch):
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'auto')
    monkeypatch.setattr(config, 'SERVERLESS', False)
    assert sessions._resolve_backend() == 'memory'


def test_explicit_backend_beats_detection(monkeypatch):
    monkeypatch.setattr(config, 'SERVERLESS', True)
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'memory')
    assert sessions._resolve_backend() == 'memory'

    monkeypatch.setattr(config, 'SERVERLESS', False)
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'firestore')
    assert sessions._resolve_backend() == 'firestore'


def test_unknown_backend_falls_back_to_auto(monkeypatch):
    monkeypatch.setattr(config, 'SESSION_BACKEND', '오타')
    monkeypatch.setattr(config, 'SERVERLESS', False)
    assert sessions._resolve_backend() == 'memory'


def test_create_helpers_follow_the_setting(monkeypatch):
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'memory')
    assert sessions.create_session_registry().backend == 'memory'
    assert sessions.create_rate_limiter().backend == 'memory'


# --- HTTP 전체 흐름 -------------------------------------------------------
def test_full_practice_flow_over_http(record_store, fake_client):
    """실제 라우트를 Firestore 세션 백엔드로 처음부터 끝까지 통과시킨다."""
    app = create_app(
        record_store=record_store,
        typing_sessions=sessions.FirestoreSessionRegistry(
            client=fake_client, transactional=_identity),
        rate_limiter=sessions.FirestoreRateLimiter(
            client=fake_client, transactional=_identity),
    )
    app.config.update(TESTING=True)
    client = app.test_client()

    assert client.get('/practice/자리').status_code == 200
    with client.session_transaction() as flask_session:
        token = flask_session['practice']['token']
        session_id = flask_session['practice']['session_id']

    assert client.post('/api/practice/start', json={'practice_token': token}).status_code == 200

    response = client.post('/api/keystroke', json={'count': 30, 'practice_token': token})
    assert response.status_code == 200
    assert response.get_json()['count'] == 30

    # 연습을 마친 상태로 만든다(Firestore 문서를 직접 고친다).
    registry = sessions.FirestoreSessionRegistry(client=fake_client, transactional=_identity)
    collection = fake_client.collection(config.FIRESTORE_SESSION_COLLECTION)
    stored = collection.docs[sessions._session_doc_id(session_id)]
    now = stored['created_at']
    stored.update({
        'started_at': now - 305.0,
        'count': 1500,
        'first_keystroke_at': now - 290.0,
        'last_keystroke_at': now,
    })

    response = client.post('/api/records', json={
        'student_id': '10218 홍길동',
        'wpm': 200,
        'accuracy': 95.0,
        'practice_token': token,
    })
    assert response.status_code == 201, response.get_json()

    # 저장 후 세션 문서는 폐기된다(1회용 토큰).
    assert registry.get(session_id) is None


def test_broken_session_backend_falls_back_to_memory_with_a_reason(monkeypatch):
    """세션 백엔드를 만들지 못해도 앱은 뜨되, 이유가 /health에 남아야 한다."""
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'firestore')
    monkeypatch.setattr(sessions, 'FirestoreSessionRegistry',
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError('연결 실패')))

    registry = sessions.create_session_registry()

    assert registry.backend == 'memory'
    assert registry.reason and '타이핑 세션을 찾을 수 없습니다' in registry.reason


def test_broken_rate_limiter_falls_back_to_memory(monkeypatch):
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'firestore')
    monkeypatch.setattr(sessions, 'FirestoreRateLimiter',
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError('연결 실패')))

    limiter = sessions.create_rate_limiter()

    assert limiter.backend == 'memory'
    assert limiter.allow('10101 가나다') is True
