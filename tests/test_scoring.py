"""점수 계산과 검증 로직 테스트."""

import scoring


def test_compute_score_matches_prd_formula():
    # score = round(타수 * (정확도/100)^2 * 100)
    assert scoring.compute_score(200, 100.0) == 20000
    assert scoring.compute_score(200, 90.0) == 16200
    assert scoring.compute_score(0, 100.0) == 0


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
    # 5분에 600타를 입력했다면 분당 120타 → 여유를 둬도 210타 이하만 인정
    assert scoring.max_plausible_wpm(600, 300) == 210.0
    assert scoring.validate_wpm_against_keystrokes(200, 600, 300)[0] is True
    assert scoring.validate_wpm_against_keystrokes(400, 600, 300)[0] is False
    # 키 입력이 전혀 없으면 여유값만 허용된다
    assert scoring.validate_wpm_against_keystrokes(500, 0, 300)[0] is False
