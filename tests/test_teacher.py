"""교사 대시보드와 예제 목록/설정(catalog) 테스트."""

import catalog
import config
import content
import store as store_module


# --- 터틀 예제 추출 -------------------------------------------------------
def test_turtle_lines_are_single_line_and_deduped():
    lines = content.EXAMPLE_SETS['turtle']['lines']

    assert 'import turtle' in lines
    assert 'screen.setup(600, 600)' in lines
    assert 'player.goto(0, -250)' in lines
    # 코드 블록에 5번 나오는 import turtle이 한 번만 남는다.
    assert lines.count('import turtle') == 1
    # 자리 연습은 한 줄 표시라 줄바꿈이 있으면 안 된다.
    assert all('\n' not in line for line in lines)
    # 마크다운 표(참고: 빈칸)의 `|` 행은 코드 블록이 아니므로 섞이면 안 된다.
    assert all('★' not in line for line in lines)


def test_jari_practice_text_comes_from_turtle_set():
    for _ in range(20):
        text = content.build_practice_text('자리')
        assert text in content.EXAMPLE_SETS['turtle']['lines']


def test_jari_uses_supplied_lines_over_default():
    text = content.build_practice_text('자리', texts=['오직 이 줄'])
    assert text == '오직 이 줄'


# --- 낱말/문장/문단이 터틀 예제에서 나온다 --------------------------------
def test_word_sentence_paragraph_come_from_turtle():
    blocks = content._extract_code_blocks(content.TURTLE_SOURCE_MARKDOWN)

    # 문단: 터틀 예제 5개(주제1~5)의 완성 코드 블록 그대로.
    assert len(content.PRACTICE_TEXTS['문단']) == 5
    assert content.PRACTICE_TEXTS['문단'] == blocks
    # 문단은 여러 줄이고, 빈 줄은 없다(타자 연습에서 빈 줄 입력은 번거롭다).
    for block in content.PRACTICE_TEXTS['문단']:
        assert '\n' in block
        assert '\n\n' not in block

    # 문장: 자리 연습과 같은, 중복 없는 코드 한 줄 목록.
    assert content.PRACTICE_TEXTS['문장'] == content.EXAMPLE_SETS['turtle']['lines']

    # 낱말: 예제별 식별자만 모은 줄. 문자열/숫자는 낱말이 아니다.
    words = content.PRACTICE_TEXTS['낱말']
    assert len(words) == 5
    assert words[0] == 'import turtle screen Screen title bgcolor setup mainloop'
    joined = ' '.join(words)
    assert 'turtle' in joined and 'forward' in joined and 'goto' in joined
    assert 'My' not in joined.split() and 'Game' not in joined.split()  # 문자열 제외
    assert '600' not in joined  # 숫자 제외


def test_word_sentence_paragraph_build_from_content():
    for mode in ('낱말', '문장', '문단'):
        for _ in range(10):
            assert content.build_practice_text(mode) in content.PRACTICE_TEXTS[mode]


# --- catalog 설정 ---------------------------------------------------------
def test_defaults_come_from_content(record_store):
    catalog._invalidate()
    settings = catalog.get_settings(record_store)

    # 네 모드 모두 기본으로 열려 있다.
    assert settings['modes']['자리'] is True
    assert settings['modes']['낱말'] is True
    assert settings['modes']['문장'] is True
    assert settings['modes']['문단'] is True
    assert settings['active_example_set'] == 'turtle'


def test_set_mode_available_persists(record_store):
    catalog._invalidate()
    catalog.set_mode_available(record_store, '낱말', True)

    # 캐시를 비우고 다시 읽어도 유지된다(DB에 저장됐다는 뜻).
    catalog._invalidate()
    assert catalog.get_settings(record_store)['modes']['낱말'] is True


def test_effective_modes_reflect_settings(record_store):
    catalog._invalidate()
    catalog.set_mode_available(record_store, '자리', False)

    modes = catalog.effective_modes(record_store)
    assert modes['자리']['available'] is False
    # 코드 기본값은 건드리지 않는다.
    assert content.PRACTICE_MODES['자리']['available'] is True


def test_unknown_mode_is_rejected(record_store):
    import pytest
    with pytest.raises(ValueError):
        catalog.set_mode_available(record_store, '없는모드', True)


def test_set_active_example_set_validates(record_store):
    import pytest
    catalog._invalidate()
    with pytest.raises(ValueError):
        catalog.set_active_example_set(record_store, '없는목록')


def test_active_example_lines_follow_selection(record_store):
    catalog._invalidate()
    lines = catalog.active_example_lines(record_store)
    assert lines == content.EXAMPLE_SETS['turtle']['lines']


def test_stored_unknown_example_set_falls_back(record_store):
    """DB에 이상한 값이 있어도 기본 목록으로 버틴다."""
    record_store.write_config('settings', {'modes': {}, 'active_example_set': '삭제된목록'})
    catalog._invalidate()

    # _merge가 알 수 없는 id를 무시하므로 기본값으로 돌아간다.
    assert catalog.active_example_set_id(record_store) == 'turtle'
    assert catalog.active_example_lines(record_store)


# --- 두 번째 예제 「주인공 이동하기」 ------------------------------------
def test_move_example_set_exists_and_derives_all_modes():
    move = content.EXAMPLE_SETS['turtle_move']
    assert move['name'] == '터틀 예제 2 · 주인공 이동하기'
    # 네 모드가 쓸 파생 텍스트가 모두 있다.
    assert move['lines'] and move['blocks'] and move['words']
    # 방향키 이동 예제의 핵심 요소가 들어 있다.
    assert 'screen.listen()' in move['lines']
    assert any('onkeypress' in line for line in move['lines'])
    # 문단(블록)은 들여쓰기를 유지한다(함수 본문).
    assert any('    x = player.xcor()' in block for block in move['blocks'])


def test_move_paragraph_always_includes_key_binding():
    """문단 연습이 늘 완성 코드(방향키 연결 포함)를 보여준다.

    예전에는 단계별로 쪼개져 있어 문단이 조각(프리픽스)만 보여 줄 때는
    방향키 연결 3줄이 안 나왔다. 완성 프로그램 하나로 두어 항상 포함한다.
    """
    move = content.EXAMPLE_SETS['turtle_move']
    assert len(move['blocks']) == 1
    for line in ('screen.listen()',
                 'screen.onkeypress(go_left, "Left")',
                 'screen.onkeypress(go_right, "Right")'):
        assert line in move['blocks'][0]
    # 문단 연습이 돌려주는 텍스트에도 반드시 들어 있다.
    assert 'screen.listen()' in content.build_practice_text('문단', texts=move['blocks'])


def test_selecting_example_set_switches_all_four_modes(record_store):
    catalog._invalidate()
    catalog.set_active_example_set(record_store, 'turtle_move')
    catalog._invalidate()

    move = content.EXAMPLE_SETS['turtle_move']
    assert catalog.active_texts(record_store, '자리') == move['lines']
    assert catalog.active_texts(record_store, '문장') == move['lines']
    assert catalog.active_texts(record_store, '문단') == move['blocks']
    assert catalog.active_texts(record_store, '낱말') == move['words']


def test_ensure_backups_covers_every_set(record_store):
    created = catalog.ensure_backups(record_store)
    assert set(created) == set(content.EXAMPLE_SETS)      # 처음엔 전부 만든다
    assert catalog.ensure_backups(record_store) == []     # 이미 있으면 다시 안 만든다

    saved = catalog.read_backup(record_store, 'turtle_move')
    assert saved['name'] == '터틀 예제 2 · 주인공 이동하기'
    assert 'screen.listen()' in saved['lines']


# --- 예제 백업 ------------------------------------------------------------
def test_backup_document_has_source_and_lines():
    doc = catalog.backup_document('turtle')
    assert doc['name'] == '터틀 타이핑 예제'
    assert '터틀 예제 코드' in doc['source_markdown']
    assert doc['line_count'] == len(doc['lines'])
    assert doc['lines']


def test_ensure_backup_is_idempotent(record_store):
    assert catalog.ensure_backup(record_store) is True    # 처음엔 만든다
    assert catalog.ensure_backup(record_store) is False   # 이미 있으면 그대로

    saved = catalog.read_backup(record_store)
    assert saved['name'] == '터틀 타이핑 예제'
    assert 'import turtle' in saved['lines']


# --- 교사 대시보드 라우트 -------------------------------------------------
def _login(client):
    return client.post('/teacher/login', data={'password': config.TEACHER_PASSWORD})


def test_dashboard_requires_login(client):
    page = client.get('/teacher')
    assert page.status_code == 200
    assert '비밀번호' in page.get_data(as_text=True)
    assert 'mode-toggle' not in page.get_data(as_text=True)


def test_wrong_password_is_rejected(client):
    response = client.post('/teacher/login', data={'password': '틀린비번'})
    assert response.status_code == 401
    assert '올바르지 않' in response.get_data(as_text=True)


def test_login_opens_dashboard(client):
    assert _login(client).status_code in (302, 303)

    page = client.get('/teacher')
    assert 'mode-toggle' in page.get_data(as_text=True)
    assert '터틀 타이핑 예제' in page.get_data(as_text=True)


def test_setters_require_authentication(client):
    assert client.post('/api/teacher/modes',
                       json={'mode': '낱말', 'available': True}).status_code == 401
    assert client.post('/api/teacher/example-set',
                       json={'id': 'turtle'}).status_code == 401


def test_toggle_mode_changes_home_page(client, app):
    catalog._invalidate()
    _login(client)

    response = client.post('/api/teacher/modes', json={'mode': '낱말', 'available': True})
    assert response.status_code == 200
    assert response.get_json()['modes']['낱말'] is True

    catalog._invalidate()
    home = client.get('/').get_data(as_text=True)
    # 낱말이 열리면 홈에 낱말 연습 시작 링크가 생긴다.
    assert '/practice/%EB%82%B1%EB%A7%90' in home or '/practice/낱말' in home


def test_example_set_endpoint_rejects_unknown(client):
    _login(client)
    response = client.post('/api/teacher/example-set', json={'id': '없는목록'})
    assert response.status_code == 400


def test_logout_closes_dashboard(client):
    _login(client)
    assert 'mode-toggle' in client.get('/teacher').get_data(as_text=True)

    client.post('/teacher/logout')
    assert 'mode-toggle' not in client.get('/teacher').get_data(as_text=True)


# --- 저장소가 죽어도 앱은 뜬다 --------------------------------------------
def test_settings_fall_back_when_store_unavailable():
    catalog._invalidate()
    broken = store_module.UnavailableStore('연결 없음')

    # read_config가 None을 돌려주므로 기본값으로 동작한다.
    settings = catalog.get_settings(broken)
    assert settings['active_example_set'] == 'turtle'
    assert settings['modes']['자리'] is True
