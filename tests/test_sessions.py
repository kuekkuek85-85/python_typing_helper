"""키 입력 집계 검증 (Codex P1: 클라이언트의 키 입력 개수를 신뢰하지 않는다)."""

import config
from sessions import RateLimiter, TypingSessionRegistry


def _registry_with_started_session():
    registry = TypingSessionRegistry()
    registry.create('s1')
    activity = registry.start('s1')
    return registry, activity


def test_reported_count_is_capped_by_elapsed_time():
    """개발자 도구로 개수를 부풀려도 경과 시간으로 설명 가능한 만큼만 인정한다."""
    registry, activity = _registry_with_started_session()

    # 시작 직후 한 번에 5000타를 주장한다.
    registry.add_keystrokes('s1', 5000)

    assert activity.reported_count == 5000
    # 버킷 크기만큼만 인정된다.
    assert activity.count == config.KEYSTROKE_BURST
    assert activity.count < 5000


def test_repeated_inflated_reports_do_not_accumulate_freely():
    registry, activity = _registry_with_started_session()

    for _ in range(20):
        registry.add_keystrokes('s1', 200)

    assert activity.reported_count == 4000
    # 시간이 거의 흐르지 않았으므로 버킷 하나 분량을 크게 넘지 못한다.
    assert activity.count <= config.KEYSTROKE_BURST + config.MAX_KEYSTROKES_PER_SECOND


def test_normal_typing_is_credited_in_full():
    """정상 타이핑(약 2초마다 소량 보고)은 전량 인정되어야 한다."""
    registry, activity = _registry_with_started_session()

    # 2초 간격으로 10타씩 = 5타/초. 한도(8타/초)보다 낮다.
    now = activity.started_at
    total = 0
    for step in range(1, 61):
        now = activity.started_at + step * 2
        activity.credit(10, now)
        total += 10

    assert activity.count == total, '정상 타이핑이 깎이면 안 된다'


def test_burst_within_bucket_is_not_lost():
    """순간적으로 빠르게 친 구간도 버킷 안에서는 그대로 인정된다."""
    registry, activity = _registry_with_started_session()

    # 시작 직후 1초 동안 40타(40타/초)를 쳐도 버킷(80)이 흡수한다.
    activity.credit(40, activity.started_at + 1)
    assert activity.count == 40


def test_credit_tracks_first_and_last_keystroke_times():
    registry, activity = _registry_with_started_session()

    registry.add_keystrokes('s1', 5)
    first = activity.first_keystroke_at
    registry.add_keystrokes('s1', 5)

    assert first is not None
    assert activity.last_keystroke_at >= first


def test_start_resets_previous_counts():
    registry, activity = _registry_with_started_session()
    registry.add_keystrokes('s1', 50)
    assert activity.count > 0

    restarted = registry.start('s1')
    assert restarted.count == 0
    assert restarted.reported_count == 0
    assert restarted.first_keystroke_at is None


def test_keystrokes_ignored_before_practice_starts():
    registry = TypingSessionRegistry()
    registry.create('s2')

    assert registry.add_keystrokes('s2', 100) is None


def test_expired_sessions_are_pruned():
    registry = TypingSessionRegistry(ttl_seconds=0)
    registry.create('old')
    registry.create('new')

    # create()가 오래된 세션을 정리한다.
    assert len(registry) <= 1


def test_rate_limiter_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(window_seconds=300, max_submissions=2)

    assert limiter.allow('10218 홍길동') is True
    assert limiter.allow('10218 홍길동') is True
    assert limiter.allow('10218 홍길동') is False
    # 다른 학생은 영향을 받지 않는다.
    assert limiter.allow('10219 김영희') is True
