"""학번 검증, 점수 계산, 기록 무결성 검증.

점수는 항상 서버에서 계산한다(PRD 5.3 공식). 클라이언트가 보낸 score는
무시하므로 콘솔에서 점수를 바꿔도 순위표에 반영되지 않는다.
"""

import re

import config

# "10218 홍길동" 형식
ID_PATTERN = re.compile(r"^\d{5}\s[가-힣]{2,4}$")

# 분당 타수 상한(물리적으로 불가능한 값 차단)
MAX_WPM = 600

# 정확도가 높은데 속도까지 비현실적인 조합
HIGH_ACCURACY_THRESHOLD = 90.0
HIGH_ACCURACY_MAX_WPM = 450

# 정확도가 낮은데 속도만 높은 조합(무작위 연타)
LOW_ACCURACY_THRESHOLD = 50.0
LOW_ACCURACY_MAX_WPM = 300

# 서버가 센 키 입력 수로부터 허용할 타수의 여유 배율/여유값.
# 네트워크 지연으로 일부 키 입력이 누락될 수 있으므로 넉넉하게 둔다.
KEYSTROKE_WPM_FACTOR = 1.5
KEYSTROKE_WPM_MARGIN = 30


def compute_score(wpm: int, accuracy: float) -> int:
    """PRD 공식: score = round(max(0, 타수) * (정확도/100)^2 * 100)"""
    safe_wpm = max(0, wpm)
    safe_accuracy = min(100.0, max(0.0, accuracy))
    return round(safe_wpm * (safe_accuracy / 100.0) ** 2 * 100)


def validate_student_id(student_id: str) -> tuple[bool, str]:
    if not ID_PATTERN.match(student_id):
        return False, '학번 이름 형식이 올바르지 않습니다. (예: 10218 홍길동)'
    return True, 'OK'


def validate_metrics(wpm: int, accuracy: float) -> tuple[bool, str]:
    """분당 타수와 정확도가 현실적인 범위인지 검사한다."""
    if not 0 <= accuracy <= 100:
        return False, '정확도는 0-100% 사이여야 합니다.'

    if not 0 <= wpm <= MAX_WPM:
        return False, f'분당 타수는 0-{MAX_WPM} 사이여야 합니다.'

    if accuracy >= HIGH_ACCURACY_THRESHOLD and wpm > HIGH_ACCURACY_MAX_WPM:
        return False, '비현실적인 성능입니다.'

    if accuracy < LOW_ACCURACY_THRESHOLD and wpm > LOW_ACCURACY_MAX_WPM:
        return False, '비일반적인 타이핑 패턴입니다.'

    return True, 'OK'


def validate_typing_activity(activity, duration_sec: int) -> tuple[bool, str]:
    """서버가 직접 센 키 입력 기록으로 실제 연습 여부를 검증한다.

    activity: sessions.TypingActivity
    """
    if activity is None:
        return False, '타이핑 세션을 찾을 수 없습니다. 다시 연습을 시작해주세요.'

    if activity.count < config.MIN_KEYSTROKES:
        return False, f'연습이 부족합니다. 최소 {config.MIN_KEYSTROKES}번 이상 타이핑해주세요.'

    if activity.span_seconds < config.MIN_TYPING_SPAN_SECONDS:
        return False, '타이핑 패턴이 비정상입니다.'

    return True, 'OK'


def max_plausible_wpm(keystroke_count: int, duration_sec: int) -> float:
    """서버가 센 키 입력 수로부터 허용 가능한 최대 타수를 계산한다."""
    if duration_sec <= 0:
        return float(MAX_WPM)
    keystrokes_per_minute = keystroke_count / (duration_sec / 60.0)
    return keystrokes_per_minute * KEYSTROKE_WPM_FACTOR + KEYSTROKE_WPM_MARGIN


def validate_wpm_against_keystrokes(wpm: int, keystroke_count: int,
                                    duration_sec: int) -> tuple[bool, str]:
    """제출된 타수가 서버가 센 키 입력 수로 설명 가능한지 검사한다."""
    if wpm > max_plausible_wpm(keystroke_count, duration_sec):
        return False, '입력 기록과 맞지 않는 타수입니다.'
    return True, 'OK'
