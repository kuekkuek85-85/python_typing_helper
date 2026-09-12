"""점수 계산과 검증 로직 테스트."""

import scoring


def test_compute_score_matches_prd_formula():
    # score = round(타수 * (정확도/100)^2 * 100)
    assert scoring.compute_score(200, 100.0) == 20000
    assert scoring.compute_score(200, 90.0) == 16200
    assert scoring.compute_score(0, 100.0) == 0


def test_compute_score_rounds_halves_up_like_javascript():
    """화면(JS Math.round)과 서버의 반올림 규칙이 같아야 한다.

    파이썬 기본 round()는 짝수 쪽으로 반올림해서 1912.5 → 1912가 되고,
    화면은 1913이 되어 학생이 본 점수와 저장값이 달라졌다.
    """
    # 34 * 0.75^2 * 100 = 1912.5 (정확히 절반)
    assert 34 * (75 / 100) ** 2 * 100 == 1912.5
    assert scoring.compute_score(34, 75.0) == 1913

    assert scoring.round_half_up(0.5) == 1
    assert scoring.round_half_up(1.5) == 2
    assert scoring.round_half_up(2.5) == 3   # round()는 2를 준다
    assert scoring.round_half_up(2.4) == 2
    assert scoring.round_half_up(0.0) == 0


def test_compute_score_matches_javascript_on_every_half_case():
    """정확히 .5가 되는 모든 조합에서 화면 공식과 일치해야 한다."""
    import math

    for wpm in range(0, scoring.MAX_WPM + 1):
        for accuracy in (25.0, 50.0, 75.0, 90.0, 100.0):
            raw = wpm * (accuracy / 100) ** 2 * 100
            javascript_result = math.floor(raw + 0.5)  # JS Math.round와 동일
            assert scoring.compute_score(wpm, accuracy) == javascript_result


def test_compute_score_clamps_negative_and_out_of_range():
    assert scoring.compute_score(-50, 90.0) == 0
    assert scoring.compute_score(100, 150.0) == scoring.compute_score(100, 100.0)
    assert scoring.compute_score(100, -10.0) == 0


def test_validate_student_id():
    assert scoring.validate_student_id('10218 홍길동')[0] is True
    assert scoring.validate_student_id('1021 홍길동')[0] is False
    assert scoring.validate_student_id('10218 Hong')[0] is False
    assert scoring.validate_student_id('10218홍길동')[0] is False
    assert scoring.validate_student_id('10218 홍')[0] is False


def test_validate_metrics_accepts_realistic_values():
    assert scoring.validate_metrics(250, 96.0)[0] is True
    assert scoring.validate_metrics(0, 100.0)[0] is True


def test_validate_metrics_rejects_impossible_values():
    assert scoring.validate_metrics(200, 120.0)[0] is False
    assert scoring.validate_metrics(scoring.MAX_WPM + 1, 90.0)[0] is False
    # 정확도가 높은데 속도까지 비현실적
    assert scoring.validate_metrics(500, 99.0)[0] is False
    # 정확도가 낮은데 속도만 높음(무작위 연타)
    assert scoring.validate_metrics(350, 20.0)[0] is False


def test_max_plausible_wpm_scales_with_keystrokes():
    # 5분에 1500타를 입력했다면 분당 300타 → 정타가 그보다 많을 수는 없다
    assert scoring.max_plausible_wpm(1500, 300) == 340.0
    assert scoring.validate_wpm_against_keystrokes(280, 1500, 300)[0] is True
    # 키 입력 수로 설명할 수 없는 타수는 거부
    assert scoring.validate_wpm_against_keystrokes(400, 1500, 300)[0] is False
    # 키 입력이 전혀 없으면 여유값만 허용된다
    assert scoring.validate_wpm_against_keystrokes(100, 0, 300)[0] is False


def test_realistic_ceiling_has_no_gap_between_accuracy_bands():
    """정확도 50~90% 구간에 속도 상한이 사실상 없던 구멍이 막혔는지 확인.

    이전에는 MAX_WPM이 600이어서 정확도 89.9%로 신고하면 600타까지 통과하고,
    정확도 90%의 상한(450타)보다 더 높은 점수를 만들 수 있었다.
    """
    assert scoring.validate_metrics(scoring.MAX_WPM + 1, 89.9)[0] is False

    best_under_90 = scoring.compute_score(scoring.MAX_WPM, 89.9)
    best_at_100 = scoring.compute_score(scoring.HIGH_ACCURACY_MAX_WPM, 100.0)
    # 정확도를 낮춰 신고하는 쪽이 더 유리해서는 안 된다.
    assert best_under_90 <= best_at_100
