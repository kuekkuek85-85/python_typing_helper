"""연습 세션 추적과 제출 빈도 제한.

두 저장소 모두 **프로세스 메모리**에만 존재한다. 그래서 웹 서버는 반드시
단일 워커(gunicorn --workers 1 --threads N)로 띄워야 한다. 워커가 여러 개면
키 입력을 받은 워커와 기록을 저장하는 워커가 달라져 "타이핑 세션을 찾을 수
없습니다" 오류가 난다. (DEPLOYMENT.md 참고)
"""

import threading
import time
from dataclasses import dataclass, field

import config


@dataclass
class TypingActivity:
    """한 번의 연습에서 서버가 인정한 키 입력 기록.

    타임스탬프를 모두 모으지 않고 개수/처음/마지막만 유지하므로 긴 연습에도
    메모리가 늘지 않는다.

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


class TypingSessionRegistry:
    """session_id별 TypingActivity 보관소."""

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
        """연습 시작 시각을 기록하고 키 입력 집계를 초기화한다."""
        now = time.time()
        with self._lock:
            activity = self._sessions.get(session_id)
            if activity is None:
                return None
            activity.started_at = now
            activity.count = 0
            activity.reported_count = 0
            activity.first_keystroke_at = None
            activity.last_keystroke_at = None
            # 연습 시작 시점에는 버킷을 가득 채워 둔다(첫 구간의 빠른 입력 흡수).
            activity.tokens = float(config.KEYSTROKE_BURST)
            activity.tokens_updated_at = now
            return activity

    def add_keystrokes(self, session_id: str, count: int) -> TypingActivity | None:
        """키 입력 개수를 누적한다. 연습이 시작되지 않았으면 무시한다.

        보고된 개수 전부를 믿지 않고, 경과 시간으로 설명 가능한 만큼만 인정한다.
        """
        now = time.time()
        with self._lock:
            activity = self._sessions.get(session_id)
            if activity is None or activity.started_at is None:
                return None

            granted = activity.credit(count, now)
            if granted > 0:
                if activity.first_keystroke_at is None:
                    activity.first_keystroke_at = now
                activity.last_keystroke_at = now
            return activity

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
    """학번별 제출 빈도 제한기."""

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
