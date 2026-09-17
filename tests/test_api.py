"""HTTP API 테스트 - 연습 시작부터 기록 저장까지."""

import config
import scoring


# --- 페이지 -------------------------------------------------------------
def test_index_renders_without_records(client):
    response = client.get('/')
    assert response.status_code == 200
    assert '명예의 전당' in response.get_data(as_text=True)


def test_practice_page_issues_token(client):
    response = client.get('/practice/자리')
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert session['practice']['mode'] == '자리'
        assert len(session['practice']['token']) > 20


def test_unknown_practice_mode_returns_404(client):
    assert client.get('/practice/없는모드').status_code == 404


def test_unknown_api_returns_json_404(client):
    response = client.get('/api/nope')
    assert response.status_code == 404
    assert 'error' in response.get_json()


def test_health_reports_backend(client):
    payload = client.get('/health').get_json()
    assert payload['backend'] == 'local'
    assert payload['database_connected'] is True


# --- 연습 텍스트 ---------------------------------------------------------
def test_practice_text_for_each_mode(client):
    for mode in ('자리', '낱말', '문장', '문단'):
        payload = client.get(f'/api/practice-text/{mode}').get_json()
        assert payload['success'] is True
        assert payload['text'].strip()


def test_practice_text_rejects_unknown_mode(client):
    response = client.get('/api/practice-text/없는모드')
    assert response.status_code == 400


def test_practice_text_avoids_immediate_repeat(client):
    first = client.get('/api/practice-text/문단').get_json()['text']
    second = client.get('/api/practice-text/문단').get_json()['text']
    assert first != second


# --- 세션/토큰 검증 -------------------------------------------------------
def test_save_without_session_is_unauthorized(client):
    response = client.post('/api/records', json={'student_id': '10218 홍길동',
                                                 'wpm': 100, 'accuracy': 95.0,
                                                 'practice_token': 'fake'})
    assert response.status_code == 401


def test_save_with_wrong_token_is_unauthorized(practice_flow):
    practice_flow.open().start().simulate()
    response = practice_flow.save(practice_token='wrong-token')
    assert response.status_code == 401


def test_keystroke_requires_started_practice(client, practice_flow):
    practice_flow.open()
    response = client.post('/api/keystroke',
                           json={'count': 5, 'practice_token': practice_flow.token})
    assert response.status_code == 409


def test_keystrokes_are_counted_and_capped(client, practice_flow):
    """부풀린 키 입력 개수는 경과 시간으로 설명 가능한 만큼만 인정된다."""
    practice_flow.open().start()

    client.post('/api/keystroke', json={'count': 10, 'practice_token': practice_flow.token})
    payload = client.post('/api/keystroke',
                          json={'count': 10_000, 'practice_token': practice_flow.token}).get_json()

    # 시작 직후이므로 버킷 크기(기본 80타)를 넘을 수 없다.
    assert payload['count'] <= config.KEYSTROKE_BURST
    assert payload['count'] < 10_000
    # app.py가 요청당 200으로 먼저 깎고(1차), sessions가 경과 시간으로 다시 깎는다(2차).
    assert practice_flow.activity().reported_count == 210


# --- 기록 저장 -----------------------------------------------------------
def test_successful_save_computes_score_on_server(practice_flow, record_store):
    practice_flow.open().start().simulate(keystrokes=800)

    response = practice_flow.save(wpm=150, accuracy=96.0, score=999999)
    assert response.status_code == 201, response.get_json()

    payload = response.get_json()
    assert payload['score'] == scoring.compute_score(150, 96.0)

    saved = record_store.top('자리')
    assert len(saved) == 1
    assert saved[0]['score'] == scoring.compute_score(150, 96.0)
    # 클라이언트가 보낸 score는 무시된다.
    assert saved[0]['score'] != 999999
    # 저장되는 연습 시간은 항상 규정 시간이다.
    assert saved[0]['duration_sec'] == config.PRACTICE_SECONDS


def test_save_rejects_bad_student_id(practice_flow):
    practice_flow.open().start().simulate()
    response = practice_flow.save(student_id='12 홍')
    assert response.status_code == 400
    assert '학번' in response.get_json()['error']


def test_save_rejects_before_practice_time_elapsed(practice_flow):
    practice_flow.open().start().simulate(elapsed=120.0, span=100.0)
    response = practice_flow.save()
    assert response.status_code == 400
    assert '종료 후 저장' in response.get_json()['error']


def test_save_rejects_after_grace_period(practice_flow):
    too_late = config.PRACTICE_SECONDS + config.SAVE_GRACE_SECONDS + 60
    practice_flow.open().start().simulate(elapsed=too_late)
    response = practice_flow.save()
    assert response.status_code == 400
    assert '시간이 경과' in response.get_json()['error']


def test_save_rejects_too_few_keystrokes(practice_flow):
    practice_flow.open().start().simulate(keystrokes=config.MIN_KEYSTROKES - 1)
    response = practice_flow.save()
    assert response.status_code == 400
    assert '연습이 부족' in response.get_json()['error']


def test_save_rejects_short_typing_span(practice_flow):
    """콘솔에서 순간적으로 키 입력을 몰아넣은 경우를 막는다."""
    practice_flow.open().start().simulate(keystrokes=2000, span=5.0)
    response = practice_flow.save()
    assert response.status_code == 400
    assert '비정상' in response.get_json()['error']


def test_save_rejects_wpm_not_supported_by_keystrokes(practice_flow):
    """키 입력 200타로 분당 400타를 주장할 수는 없다(정타 수 <= 총 키 입력 수)."""
    practice_flow.open().start().simulate(keystrokes=200)
    response = practice_flow.save(wpm=400, accuracy=60.0)
    assert response.status_code == 400
    assert '입력 기록' in response.get_json()['error']


def test_save_rejects_unrealistic_metrics(practice_flow):
    practice_flow.open().start().simulate(keystrokes=5000)
    response = practice_flow.save(wpm=430, accuracy=99.0)
    assert response.status_code == 400
    assert '비현실적' in response.get_json()['error']


def test_save_rejects_wpm_above_absolute_ceiling(practice_flow):
    practice_flow.open().start().simulate(keystrokes=5000)
    response = practice_flow.save(wpm=scoring.MAX_WPM + 1, accuracy=70.0)
    assert response.status_code == 400
    assert '분당 타수' in response.get_json()['error']


def test_token_is_single_use(practice_flow):
    practice_flow.open().start().simulate()
    assert practice_flow.save().status_code == 201

    # 같은 토큰으로 다시 저장할 수 없다.
    assert practice_flow.save().status_code == 401


def test_rate_limit_blocks_repeated_submissions(app, practice_flow):
    app.extensions['rate_limiter'].reset()

    for _ in range(config.MAX_SUBMISSIONS_PER_WINDOW):
        practice_flow.open().start().simulate()
        assert practice_flow.save().status_code == 201

    practice_flow.open().start().simulate()
    response = practice_flow.save()
    assert response.status_code == 429


def test_failed_validation_does_not_consume_rate_limit(app, practice_flow):
    app.extensions['rate_limiter'].reset()

    for _ in range(5):
        practice_flow.open().start().simulate()
        assert practice_flow.save(student_id='bad id').status_code == 400

    practice_flow.open().start().simulate()
    assert practice_flow.save().status_code == 201


# --- 조회 API ------------------------------------------------------------
def test_top_and_pagination_apis(client, practice_flow, app):
    app.extensions['rate_limiter'].reset()
    practice_flow.open().start().simulate()
    assert practice_flow.save().status_code == 201

    top = client.get('/api/records/top?mode=자리').get_json()
    assert top['total'] == 1
    assert top['records'][0]['student_id'] == '10218 홍길동'
    assert top['records'][0]['created_at'].endswith('+09:00')

    page = client.get('/api/records?mode=자리&limit=1&offset=0').get_json()
    assert page['pagination'] == {
        'limit': 1, 'offset': 0, 'total': 1, 'has_more': False, 'current_count': 1,
    }


def test_records_api_rejects_bad_mode_and_params(client):
    assert client.get('/api/records?mode=없는모드').status_code == 400
    assert client.get('/api/records?mode=자리&limit=abc').status_code == 400
    assert client.get('/api/records/top?mode=없는모드').status_code == 400


def test_records_api_clamps_limit_and_offset(client):
    payload = client.get('/api/records?mode=자리&limit=999999&offset=-5').get_json()
    assert payload['pagination']['limit'] == config.MAX_PAGE_SIZE
    assert payload['pagination']['offset'] == 0


def test_stats_endpoint_is_removed(client):
    """전체 통계 API는 v0.8에서 제거했다(모든 기록을 읽는데 쓰는 화면이 없었음).

    다시 추가한다면 저장 시 요약 문서를 갱신하는 방식이어야 한다.
    """
    response = client.get('/api/records/stats')
    assert response.status_code == 404


# --- 정적 파일 캐시 ------------------------------------------------------
def test_static_urls_carry_a_content_hash(client):
    """정적 파일에 7일 캐시를 걸었으므로 URL에 내용 해시가 붙어야 한다.

    해시가 없으면 app.js를 고쳐도 학생 브라우저가 최대 일주일 동안 옛 파일을
    쓴다. 점수 공식이 바뀌면 화면 점수와 저장 점수가 어긋난다(CLAUDE.md 2번).
    """
    import re

    page = client.get('/practice/자리').get_data(as_text=True)
    scripts = re.findall(r'src="(/static/js/[^"]+)"', page)

    assert scripts, '연습 화면이 JS를 불러오지 않는다'
    for url in scripts:
        assert re.search(r'\?v=[0-9a-f]{8}$', url), f'해시가 없다: {url}'


def test_static_hash_changes_with_content(app, tmp_path):
    """내용이 바뀌면 해시도 바뀌어야 캐시가 갱신된다."""
    import re

    import app as app_module

    static_dir = tmp_path / 'static'
    static_dir.mkdir()
    target = static_dir / 'probe.js'

    def url_for_probe():
        flask_app = app_module.create_app(record_store=app.extensions['record_store'])
        flask_app.static_folder = str(static_dir)
        app_module._register_static_versioning(flask_app)
        with flask_app.test_request_context():
            from flask import url_for
            return url_for('static', filename='probe.js')

    target.write_text('console.log(1);')
    first = url_for_probe()
    target.write_text('console.log(2);')
    second = url_for_probe()

    assert re.search(r'\?v=[0-9a-f]{8}$', first)
    assert first != second, '내용이 바뀌었는데 URL이 같으면 캐시가 안 갱신된다'


def test_missing_static_file_does_not_break_rendering(app):
    """없는 파일이라도 url_for가 예외를 내면 안 된다(404는 라우팅이 낼 일)."""
    with app.test_request_context():
        from flask import url_for
        url = url_for('static', filename='없는파일.js')

    # 해시는 붙지 않지만 URL 자체는 정상적으로 만들어진다.
    assert url.startswith('/static/')
    assert '?v=' not in url
