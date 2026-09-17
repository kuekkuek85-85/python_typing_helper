"""연습 세션 추적과 제출 빈도 제한.

두 가지 백엔드가 있고 `config.SESSION_BACKEND`가 고른다.

- **memory**: 프로세스 메모리. 빠르고 비용이 0이지만 **단일 워커에서만** 동작한다
  (`gunicorn --workers 1 --threads N`). 워커가 여러 개면 키 입력을 받은 워커와
  기록을 저장하는 워커가 달라져 "타이핑 세션을 찾을 수 없습니다" 오류가 난다.
- **firestore**: Firestore 문서. 요청마다 프로세스가 달라지는 서버리스(Vercel)에서
  쓴다. 느리고 쓰기 비용이 들지만 인스턴스가 몇 개로 늘어나도 상관없다.

두 백엔드는 같은 상태 전이 함수(`_apply_start`, `_apply_keystrokes`)를 공유한다.
부정행위 방지 규칙이 백엔드마다 달라지면 안 되기 때문이다. 백엔드가 하는 일은
그 함수를 **어디서 읽어 와 어디에 쓰는지**뿐이다.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import config

logger = logging.getLogger(__name__)

# 서버리스인데 자격 증명이 없다는 경고를 한 번만 남기기 위한 플래그.
_serverless_without_credentials_warned = False


@dataclass
class TypingActivity:
    """한 번의 연습에서 서버가 인정한 키 입력 기록.

    타임스탬프를 모두 모으지 않고 개수/처음/마지막만 유지하므로 긴 연습에도
    메모리(와 Firestore 문서 크기)가 늘지 않는다.

    브라우저는 키 입력 **개수만** 보고하므로 값 자체는 신뢰할 수 없다. 그래서
    토큰 버킷으로 "경과 시간으로 설명할 수 있는 양"만 `count`에 반영한다.
    (`reported_count`는 클라이언트가 주장한 원래 값이며 진단용으로만 남긴다.)
    """

    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    count: int = 0
    reported_count: int = 0
    first_keystroke_at: float | None = None
    last_keystroke_at: float | None = None
    # 남은 토큰과 마지막 충전 시각. 시작 시 버킷을 가득 채운다.
    tokens: float = 0.0
    tokens_updated_at: float | None = None

    @property
    def span_seconds(self) -> float:
        """첫 키 입력과 마지막 키 입력 사이의 시간(초)."""
        if self.first_keystroke_at is None or self.last_keystroke_at is None:
            return 0.0
        return self.last_keystroke_at - self.first_keystroke_at

    @property
    def elapsed_seconds(self) -> float:
        """연습 시작 버튼을 누른 뒤 지난 시간(초). 시작 전이면 0."""
        if self.started_at is None:
            return 0.0
        return time.time() - self.started_at

    def credit(self, reported: int, now: float) -> int:
        """보고된 키 입력 중 경과 시간으로 설명 가능한 만큼만 인정한다.

        반환값은 이번에 인정된 개수. 정상 타이핑은 평균 속도가 한도보다 낮아
        전량 인정되고, 개발자 도구로 개수를 부풀린 경우에만 깎인다.
        """
        self.reported_count += reported

        elapsed = 0.0 if self.tokens_updated_at is None else max(0.0, now - self.tokens_updated_at)
        self.tokens = min(
            float(config.KEYSTROKE_BURST),
            self.tokens + elapsed * config.MAX_KEYSTROKES_PER_SECOND,
        )
        self.tokens_updated_at = now

        granted = int(min(reported, self.tokens))
        self.tokens -= granted
        self.count += granted
        return granted

    # --- 직렬화 (Firestore 백엔드용) ------------------------------------
    FIELDS = ('created_at', 'started_at', 'count', 'reported_count',
              'first_keystroke_at', 'last_keystroke_at', 'tokens', 'tokens_updated_at')

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self.FIELDS}

    @classmethod
    def from_dict(cls, data: dict) -> 'TypingActivity':
        """Firestore 문서를 되돌린다. 값이 빠졌거나 형식이 틀려도 죽지 않는다."""
        activity = cls(created_at=_as_float(data.get('created_at')) or time.time())
        activity.started_at = _as_float(data.get('started_at'))
        activity.count = _as_int(data.get('count'))
        activity.reported_count = _as_int(data.get('reported_count'))
        activity.first_keystroke_at = _as_float(data.get('first_keystroke_at'))
        activity.last_keystroke_at = _as_float(data.get('last_keystroke_at'))
        activity.tokens = _as_float(data.get('tokens')) or 0.0
        activity.tokens_updated_at = _as_float(data.get('tokens_updated_at'))
        return activity


def _as_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# --- 상태 전이 (두 백엔드가 공유한다) ------------------------------------
def _apply_start(activity: TypingActivity, now: float) -> bool:
    """연습 시작 시각을 기록하고 키 입력 집계를 초기화한다."""
    activity.started_at = now
    activity.count = 0
    activity.reported_count = 0
    activity.first_keystroke_at = None
    activity.last_keystroke_at = None
    # 연습 시작 시점에는 버킷을 가득 채워 둔다(첫 구간의 빠른 입력 흡수).
    activity.tokens = float(config.KEYSTROKE_BURST)
    activity.tokens_updated_at = now
    return True


def _apply_keystrokes(activity: TypingActivity, count: int, now: float) -> bool:
    """키 입력 개수를 누적한다. 연습이 시작되지 않았으면 False."""
    if activity.started_at is None:
        return False

    granted = activity.credit(count, now)
    if granted > 0:
        if activity.first_keystroke_at is None:
            activity.first_keystroke_at = now
        activity.last_keystroke_at = now
    return True


# --- 메모리 백엔드 --------------------------------------------------------
class TypingSessionRegistry:
    """session_id별 TypingActivity 보관소(프로세스 메모리).

    ⚠️ 단일 워커에서만 동작한다. 여러 인스턴스로 늘어나는 배포에서는
    `FirestoreSessionRegistry`를 쓴다.
    """

    backend = 'memory'

    def __init__(self, ttl_seconds: int | None = None):
        self._ttl = ttl_seconds if ttl_seconds is not None else config.SESSION_TTL_SECONDS
        self._lock = threading.Lock()
        self._sessions: dict[str, TypingActivity] = {}

    def create(self, session_id: str) -> TypingActivity:
        """새 연습 세션을 등록한다(이미 있으면 초기화)."""
        activity = TypingActivity()
        with self._lock:
            self._prune_locked()
            self._sessions[session_id] = activity
        return activity

    def get(self, session_id: str | None) -> TypingActivity | None:
        if not session_id:
            return None
        with self._lock:
            return self._sessions.get(session_id)

    def start(self, session_id: str) -> TypingActivity | None:
        return self._mutate(session_id, _apply_start)

    def add_keystrokes(self, session_id: str, count: int) -> TypingActivity | None:
        """키 입력 개수를 누적한다. 연습이 시작되지 않았으면 무시한다."""
        return self._mutate(session_id, lambda activity, now: _apply_keystrokes(
            activity, count, now))

    def _mutate(self, session_id: str | None, apply_fn) -> TypingActivity | None:
        if not session_id:
            return None
        with self._lock:
            activity = self._sessions.get(session_id)
            if activity is None:
                return None
            return activity if apply_fn(activity, time.time()) else None

    def discard(self, session_id: str | None) -> None:
        if not session_id:
            return
        with self._lock:
            self._sessions.pop(session_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)

    def _prune_locked(self) -> None:
        cutoff = time.time() - self._ttl
        stale = [key for key, value in self._sessions.items() if value.created_at < cutoff]
        for key in stale:
            del self._sessions[key]


class RateLimiter:
    """학번별 제출 빈도 제한기(프로세스 메모리)."""

    backend = 'memory'

    def __init__(self, window_seconds: int | None = None, max_submissions: int | None = None):
        self._window = window_seconds if window_seconds is not None else config.RATE_LIMIT_WINDOW
        self._max = (max_submissions if max_submissions is not None
                     else config.MAX_SUBMISSIONS_PER_WINDOW)
        self._lock = threading.Lock()
        self._log: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        """제출을 허용하면 기록을 남기고 True, 한도를 넘으면 False."""
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            # 창을 벗어난 기록은 전체적으로 정리해 메모리가 계속 늘지 않게 한다.
            for logged_key in list(self._log):
                recent = [ts for ts in self._log[logged_key] if ts > cutoff]
                if recent:
                    self._log[logged_key] = recent
                else:
                    del self._log[logged_key]

            attempts = self._log.setdefault(key, [])
            if len(attempts) >= self._max:
                return False
            attempts.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._log.clear()


# --- Firestore 백엔드 -----------------------------------------------------
def _firestore_transactional(func):
    """실제 Firestore 트랜잭션으로 감싼다(테스트에서 교체할 수 있도록 분리)."""
    from firebase_admin import firestore

    return firestore.transactional(func)


def _firestore_client():
    """Firestore 클라이언트를 만든다. 실패하면 무엇을 고쳐야 하는지 말해 준다.

    이 예외는 앱이 뜨기 전에 나므로, 서버리스에서는 배포 실패나 정체불명의 500으로만
    보인다. 원래 메시지(`DefaultCredentialsError`)만으로는 배포 로그에서 원인을
    찾기 어렵다.
    """
    import store

    try:
        return store.create_firestore_client()
    except Exception as error:
        raise RuntimeError(
            'SESSION_BACKEND=firestore인데 Firestore에 연결할 수 없습니다. '
            'FIREBASE_SERVICE_ACCOUNT_JSON(한 줄 JSON)이 설정되어 있는지 확인하세요. '
            f'원인: {error}'
        ) from error


def _session_doc_id(session_id: str) -> str:
    """session_id를 Firestore 문서 ID로 바꾼다.

    session_id는 `secrets.token_urlsafe(16)`이라 `_`·`-`가 섞여 있다. Firestore는
    `__...__` 형태의 문서 ID를 예약해 두었으므로 접두사를 붙여 그 형태가 될 수
    없게 만든다. (사람이 콘솔에서 알아볼 수 있도록 해시하지 않는다.)
    """
    return f's_{session_id}'


def _rate_limit_doc_id(key: str) -> str:
    """학번을 문서 ID로 바꾼다.

    학번에는 공백과 한글 이름이 들어 있다. 해시해서 **연습 기록 외에 학생 이름이
    남는 곳을 늘리지 않고**, 동시에 문서 ID 제약도 신경 쓰지 않게 한다.
    """
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def _mutate_document(transaction, doc_ref, apply_fn, expires_at):
    """문서를 읽어 상태 전이를 적용하고 다시 쓴다(트랜잭션 본문).

    `@firestore.transactional`이 이 함수를 감싸므로, 읽은 뒤 쓰기 전에 다른
    인스턴스가 같은 문서를 고치면 Firestore가 자동으로 재시도한다. 토큰 버킷은
    읽고-고쳐-쓰는 연산이라 이 보호가 없으면 동시에 도착한 두 요청이 서로의
    차감을 덮어써 인정량이 부풀 수 있다.
    """
    snapshot = doc_ref.get(transaction=transaction)
    if not getattr(snapshot, 'exists', False):
        return None

    activity = TypingActivity.from_dict(snapshot.to_dict() or {})
    if not apply_fn(activity, time.time()):
        return None

    transaction.set(doc_ref, {**activity.to_dict(), 'expires_at': expires_at})
    return activity


class FirestoreSessionRegistry:
    """연습 세션을 Firestore 문서로 보관한다(서버리스용).

    요청 한 번에 문서 읽기 1회 + 쓰기 1회가 든다. 5분 연습 한 번의 쓰기 횟수는
    `PRACTICE_SECONDS / (KEYSTROKE_FLUSH_MS/1000) + 2` 정도다(기본값 32회).

    버려진 세션(학생이 탭을 닫은 경우)은 `expires_at` 필드가 남으므로 Firestore
    **TTL 정책**으로 자동 삭제한다. 설정 방법은 DEPLOYMENT.md 참고. 정책을 걸지
    않아도 동작에는 문제가 없고 문서만 쌓인다.
    """

    backend = 'firestore'

    def __init__(self, client=None, collection_name: str | None = None,
                 ttl_seconds: int | None = None, transactional=None):
        self._ttl = ttl_seconds if ttl_seconds is not None else config.SESSION_TTL_SECONDS
        self._collection_name = collection_name or config.FIRESTORE_SESSION_COLLECTION
        self._transactional = transactional or _firestore_transactional
        self._client = client if client is not None else _firestore_client()

    def _doc(self, session_id: str):
        return (self._client.collection(self._collection_name)
                .document(_session_doc_id(session_id)))

    def _expires_at(self) -> datetime:
        """TTL 정책이 볼 만료 시각.

        **반드시 datetime이어야 한다.** Firestore TTL 정책은 타임스탬프 타입
        필드만 만료 대상으로 본다. Unix 초(float)로 쓰면 정책을 걸어 두어도
        아무것도 지워지지 않고 문서가 계속 쌓인다.
        """
        return datetime.now(timezone.utc) + timedelta(seconds=self._ttl)

    def create(self, session_id: str) -> TypingActivity:
        activity = TypingActivity()
        self._doc(session_id).set({**activity.to_dict(), 'expires_at': self._expires_at()})
        return activity

    def get(self, session_id: str | None) -> TypingActivity | None:
        if not session_id:
            return None
        snapshot = self._doc(session_id).get()
        if not getattr(snapshot, 'exists', False):
            return None
        return TypingActivity.from_dict(snapshot.to_dict() or {})

    def start(self, session_id: str) -> TypingActivity | None:
        try:
            return self._mutate(session_id, _apply_start)
        except Exception as error:  # noqa: BLE001
            # 라우트가 409 "다시 시작해주세요"로 안내한다. 학생이 바로 재시도할 수 있다.
            logger.warning("연습 시작을 기록하지 못했습니다: %s", error)
            return None

    def add_keystrokes(self, session_id: str, count: int) -> TypingActivity | None:
        try:
            return self._mutate(session_id, lambda activity, now: _apply_keystrokes(
                activity, count, now))
        except Exception as error:  # noqa: BLE001
            # 같은 문서에 요청이 몰리면 트랜잭션이 재시도를 소진하고 실패한다.
            # 키 입력 보고는 **잃어도 되는 값**이다. 이번 묶음만 버리고 현재 상태를
            # 돌려준다 — 여기서 예외를 올리면 연습 중에 500이 나고, 세션이 살아
            # 있는데도 학생 화면에는 오류가 뜬다.
            logger.warning("키 입력 보고를 반영하지 못했습니다(이번 묶음은 버립니다): %s", error)
            return self.get(session_id)

    def _mutate(self, session_id: str | None, apply_fn) -> TypingActivity | None:
        if not session_id:
            return None
        runner = self._transactional(_mutate_document)
        return runner(self._transaction(), self._doc(session_id), apply_fn,
                      self._expires_at())

    def _transaction(self):
        """재시도 횟수를 늘린 트랜잭션.

        SDK 기본값은 5회다. 한 학생의 보고는 10초 간격이라 원래 겹치지 않지만,
        네트워크가 잠시 막혔다가 여러 묶음이 한꺼번에 도착하면 같은 문서를 두고
        경합한다. 그때 재시도가 모자라면 그 묶음이 통째로 버려진다.
        """
        try:
            return self._client.transaction(max_attempts=config.FIRESTORE_MAX_ATTEMPTS)
        except TypeError:  # 구버전 SDK
            return self._client.transaction()

    def discard(self, session_id: str | None) -> None:
        if not session_id:
            return
        try:
            self._doc(session_id).delete()
        except Exception as error:  # noqa: BLE001 - 정리 실패가 저장을 막으면 안 된다
            logger.warning("연습 세션 문서를 지우지 못했습니다(TTL로 정리됩니다): %s", error)


def _allow_within_window(transaction, doc_ref, now: float, window: float, maximum: int) -> bool:
    """제출 기록을 읽어 한도를 확인하고, 허용되면 지금 시각을 덧붙인다."""
    snapshot = doc_ref.get(transaction=transaction)
    data = snapshot.to_dict() if getattr(snapshot, 'exists', False) else None

    cutoff = now - window
    raw = (data or {}).get('attempts') or []
    attempts = [value for value in (_as_float(item) for item in raw)
                if value is not None and value > cutoff]

    if len(attempts) >= maximum:
        return False

    attempts.append(now)
    transaction.set(doc_ref, {
        'attempts': attempts,
        # 세션 문서와 같은 이유로 타임스탬프 타입이어야 한다(TTL 정책).
        'expires_at': datetime.fromtimestamp(now + window, tz=timezone.utc),
    })
    return True


class FirestoreRateLimiter:
    """학번별 제출 빈도 제한기(Firestore).

    저장에 성공한 제출에만 쓰기가 발생하므로(app.py는 모든 검증을 통과한 뒤에만
    호출한다) 비용은 연습 횟수에 비례한다.
    """

    backend = 'firestore'

    def __init__(self, client=None, collection_name: str | None = None,
                 window_seconds: int | None = None, max_submissions: int | None = None,
                 transactional=None):
        self._window = window_seconds if window_seconds is not None else config.RATE_LIMIT_WINDOW
        self._max = (max_submissions if max_submissions is not None
                     else config.MAX_SUBMISSIONS_PER_WINDOW)
        self._collection_name = collection_name or config.FIRESTORE_RATE_LIMIT_COLLECTION
        self._transactional = transactional or _firestore_transactional
        self._client = client if client is not None else _firestore_client()

    def allow(self, key: str) -> bool:
        doc_ref = (self._client.collection(self._collection_name)
                   .document(_rate_limit_doc_id(key)))
        try:
            runner = self._transactional(_allow_within_window)
            try:
                transaction = self._client.transaction(
                    max_attempts=config.FIRESTORE_MAX_ATTEMPTS)
            except TypeError:  # 구버전 SDK
                transaction = self._client.transaction()
            return runner(transaction, doc_ref, time.time(), float(self._window), self._max)
        except Exception as error:  # noqa: BLE001
            # 빈도 제한은 보조 장치다. Firestore가 잠시 흔들린다고 해서 정상적으로
            # 연습을 마친 학생의 저장을 막지는 않는다.
            logger.warning("제출 빈도 제한을 확인하지 못해 통과시킵니다: %s", error)
            return True

    def reset(self) -> None:
        """테스트용. 운영에서는 expires_at + TTL 정책으로 정리된다."""
        for doc in self._client.collection(self._collection_name).stream():
            doc.reference.delete()


# --- 백엔드 선택 ----------------------------------------------------------
def _resolve_backend() -> str:
    backend = config.SESSION_BACKEND
    if backend in {'memory', 'firestore'}:
        return backend

    if backend != 'auto':
        logger.warning("알 수 없는 SESSION_BACKEND=%r → auto로 처리합니다.", backend)

    if not config.SERVERLESS:
        return 'memory'

    # 서버리스에서 memory를 쓰면 요청마다 프로세스가 달라져 연습 세션이 사라진다.
    # 그렇다고 자격 증명 없이 firestore를 고르면 **앱이 아예 뜨지 않는다** —
    # Firestore 클라이언트를 만들다 예외가 나고, 서버리스에서는 그게 배포 실패나
    # 정체불명의 500으로만 보인다. 그보다는 뜨게 두고 /health가 무엇이 잘못됐는지
    # 말하게 하는 편이 낫다.
    import store

    if store.firebase_credentials_available():
        return 'firestore'

    # 세션 보관소와 빈도 제한기가 각각 물어보므로 경고는 한 번만 남긴다.
    global _serverless_without_credentials_warned
    if not _serverless_without_credentials_warned:
        _serverless_without_credentials_warned = True
        logger.error(
            "서버리스 환경인데 Firebase 자격 증명이 없어 연습 세션을 프로세스 메모리에 "
            "둡니다. 인스턴스가 여러 개로 늘어나면 학생이 기록을 저장할 때 "
            "'타이핑 세션을 찾을 수 없습니다' 오류가 납니다. "
            "FIREBASE_SERVICE_ACCOUNT_JSON과 SESSION_BACKEND=firestore를 설정하세요."
        )
    return 'memory'


def create_session_registry():
    """config.SESSION_BACKEND에 따라 연습 세션 보관소를 만든다."""
    if _resolve_backend() == 'firestore':
        return FirestoreSessionRegistry()
    return TypingSessionRegistry()


def create_rate_limiter():
    """config.SESSION_BACKEND에 따라 제출 빈도 제한기를 만든다."""
    if _resolve_backend() == 'firestore':
        return FirestoreRateLimiter()
    return RateLimiter()
