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


# --- 게임 순위표 (서버 저장) ----------------------------------------------
def _save(client, student_id, score, game='word-shooter'):
    return client.post('/api/game/records',
                       json={'game': game, 'student_id': student_id, 'score': score})


def test_game_score_saves_and_appears_in_leaderboard(client):
    assert _save(client, '10218 홍길동', 120).status_code == 201

    board = client.get('/api/game/records?game=word-shooter').get_json()
    assert board['success'] is True
    names = [r['student_id'] for r in board['records']]
    assert '10218 홍길동' in names
    top = board['records'][0]
    assert top['rank'] == 1 and top['score'] == 120


def test_game_leaderboard_is_ranked_by_score(client):
    _save(client, '10101 김철수', 50)
    _save(client, '10102 이영희', 300)
    _save(client, '10103 박민수', 150)

    records = client.get('/api/game/records?game=word-shooter').get_json()['records']
    scores = [r['score'] for r in records]
    assert scores == sorted(scores, reverse=True)
    assert records[0]['student_id'] == '10102 이영희'
    assert records[0]['rank'] == 1


def test_game_score_rejects_bad_student_id(client):
    assert _save(client, '홍길동', 100).status_code == 400
    assert _save(client, '', 100).status_code == 400


def test_game_score_rejects_bad_score(client):
    import config
    assert _save(client, '10218 홍길동', -1).status_code == 400
    assert _save(client, '10218 홍길동', config.GAME_MAX_SCORE + 1).status_code == 400
    # 문자열·불리언 점수도 거부한다.
    assert client.post('/api/game/records',
                       json={'game': 'word-shooter', 'student_id': '10218 홍길동',
                             'score': 'abc'}).status_code == 400
    assert client.post('/api/game/records',
                       json={'game': 'word-shooter', 'student_id': '10218 홍길동',
                             'score': True}).status_code == 400


def test_unknown_game_is_rejected(client):
    assert _save(client, '10218 홍길동', 100, game='없는게임').status_code == 400
    assert client.get('/api/game/records?game=없는게임').status_code == 400


def test_game_scores_are_separate_from_practice_leaderboard(client, record_store):
    """게임 점수는 연습 명예의 전당(자리 등)에 절대 섞이지 않는다."""
    _save(client, '10218 홍길동', 500)

    # 연습 모드 순위에는 게임 기록이 없다.
    for mode in ('자리', '낱말', '문장', '문단'):
        assert record_store.count_for_mode(mode) == 0
    # 게임 네임스페이스에만 들어간다.
    assert record_store.count_for_mode('game:word-shooter') == 1

