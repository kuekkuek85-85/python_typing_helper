"""타자 게임(낱말 슈팅) 테스트."""

import content


def test_game_words_are_nonempty_strings():
    assert content.GAME_WORDS
    assert all(isinstance(w, str) and w for w in content.GAME_WORDS)
    # 중복이 없어야 떨어질 때 정확 일치가 헷갈리지 않는다.
    assert len(content.GAME_WORDS) == len(set(content.GAME_WORDS))
    # 학생들이 연습에서 본 낱말이 들어 있다.
    assert 'print' in content.GAME_WORDS
    assert 'turtle' in content.GAME_WORDS


def test_game_page_renders_with_words(client):
    page = client.get('/game/word-shooter')
    assert page.status_code == 200

    html = page.get_data(as_text=True)
    assert 'gameArea' in html          # 게임 영역
    assert 'gameInput' in html         # 입력창
    assert 'game_word_shooter.js' in html
    # 낱말 풀이 페이지에 내려간다(JS가 window.gameWords로 읽는다).
    assert 'turtle' in html
    assert 'print' in html


def test_game_is_linked_from_home(client):
    home = client.get('/').get_data(as_text=True)
    assert '/game/word-shooter' in home
