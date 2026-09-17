"""저장소(정렬·페이지네이션) 테스트."""

from datetime import datetime, timedelta, timezone

import store


def _add(record_store, student_id, mode='자리', wpm=100, accuracy=90.0, score=None,
         minutes_ago=0):
    created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return record_store.add(
        student_id=student_id,
        mode=mode,
        wpm=wpm,
        accuracy=accuracy,
        score=score if score is not None else wpm,
        duration_sec=300,
        created_at=created_at,
    )


def test_records_sorted_by_score_then_accuracy_then_wpm_then_time(record_store):
    _add(record_store, '10101 가나다', score=100, accuracy=90.0, wpm=100)
    _add(record_store, '10102 라마바', score=200, accuracy=80.0, wpm=100)
    _add(record_store, '10103 사아자', score=200, accuracy=95.0, wpm=100)
    _add(record_store, '10104 차카타', score=200, accuracy=95.0, wpm=150)

    names = [record['student_id'] for record in record_store.top('자리')]
    assert names == ['10104 차카타', '10103 사아자', '10102 라마바', '10101 가나다']


def test_tie_broken_by_earlier_record(record_store):
    _add(record_store, '10201 늦은이', score=300, accuracy=90.0, wpm=100, minutes_ago=1)
    _add(record_store, '10202 빠른이', score=300, accuracy=90.0, wpm=100, minutes_ago=10)

    names = [record['student_id'] for record in record_store.top('자리')]
    assert names == ['10202 빠른이', '10201 늦은이']


def test_mode_isolation_and_pagination(record_store):
    for index in range(12):
        _add(record_store, f'103{index:02d} 홍길동', mode='자리', score=100 + index)
    _add(record_store, '10999 김철수', mode='낱말', score=999)

    assert len(record_store.top('자리')) == 10

    page_one, total = record_store.page('자리', limit=5, offset=0)
    page_two, _ = record_store.page('자리', limit=5, offset=5)
    assert total == 12
    assert len(page_one) == 5
    assert not set(r['id'] for r in page_one) & set(r['id'] for r in page_two)

    words, words_total = record_store.page('낱말', limit=10, offset=0)
    assert words_total == 1
    assert words[0]['student_id'] == '10999 김철수'


def test_records_survive_reload(record_store, tmp_path):
    _add(record_store, '10501 가나다', score=500)

    reopened = store.LocalJsonStore(path=record_store.path)
    records = reopened.top('자리')
    assert len(records) == 1
    assert records[0]['student_id'] == '10501 가나다'


def test_api_dict_returns_kst_timestamp(record_store):
    created_at = datetime(2026, 3, 1, 0, 30, tzinfo=timezone.utc)
    saved = _add(record_store, '10601 가나다')
    saved['created_at'] = created_at

    payload = store.to_api_dict(saved)
    # UTC 00:30 → KST 09:30
    assert payload['created_at'].startswith('2026-03-01T09:30')
    assert payload['created_at'].endswith('+09:00')


def test_corrupted_local_file_does_not_crash(tmp_path):
    path = tmp_path / 'broken.json'
    path.write_text('{ not valid json', encoding='utf-8')

    record_store = store.LocalJsonStore(path=str(path))
    assert record_store.top('자리') == []
    # 손상된 파일이어도 새 기록은 저장된다.
    _add(record_store, '10701 가나다')
    assert len(record_store.top('자리')) == 1


def test_read_only_filesystem_does_not_crash_at_startup(tmp_path, monkeypatch):
    """읽기 전용 파일 시스템에서도 저장소 객체를 만들 수 있어야 한다.

    서버리스(Vercel)의 런타임 파일 시스템은 /tmp 말고는 읽기 전용이다.
    LocalJsonStore는 create_app() 안에서 만들어지므로, 여기서 예외가 올라가면
    앱이 임포트 중에 죽고 배포 실패로만 보인다. 기록을 못 남긴다는 사실은
    /health가 알려 주므로, 죽는 것보다 뜨는 편이 낫다.
    """
    import os

    def read_only(*args, **kwargs):
        raise OSError(30, 'Read-only file system')

    monkeypatch.setattr(os, 'makedirs', read_only)

    record_store = store.LocalJsonStore(path=str(tmp_path / 'nope' / 'records.json'))

    # 뜨기는 하되, 기록이 없다는 것은 정직하게 드러낸다.
    assert record_store.backend == 'local'
    assert record_store.top('자리') == []


def test_app_boots_when_storage_directory_cannot_be_created(monkeypatch):
    """앱 전체가 뜨는지 확인한다(임포트 경로 전체)."""
    import os

    import app as app_module
    import config

    monkeypatch.setattr(config, 'STORE_BACKEND', 'local')
    monkeypatch.setattr(config, 'LOCAL_DB_PATH', '/읽기전용/records.json')
    monkeypatch.setattr(config, 'SESSION_BACKEND', 'memory')
    monkeypatch.setattr(os, 'makedirs', lambda *a, **k: (_ for _ in ()).throw(
        OSError(30, 'Read-only file system')))

    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True)

    response = flask_app.test_client().get('/health')
    assert response.status_code in (200, 503)
    assert response.get_json()['backend'] == 'local'


# --- 설정 오류로 죽지 않는다 ---------------------------------------------
def test_broken_firestore_config_does_not_crash_the_app(monkeypatch):
    """`STORE_BACKEND=firestore`인데 자격 증명이 잘못돼도 앱은 떠야 한다.

    서버리스에서 임포트 중 예외는 `500 FUNCTION_INVOCATION_FAILED` 한 줄로만
    보인다. 무엇이 잘못됐는지 알 방법이 없다. 대신 떠서 /health가 말하게 한다.
    """
    import config

    monkeypatch.setattr(config, 'STORE_BACKEND', 'firestore')
    monkeypatch.setattr(store, 'FirestoreStore', lambda *a, **k: (_ for _ in ()).throw(
        ValueError('Invalid control character at: line 1 column 172')))

    record_store = store.create_store()

    assert record_store.backend == 'unavailable'
    assert record_store.reason and 'FIREBASE_SERVICE_ACCOUNT_JSON' in record_store.reason
    assert record_store.ping() is False


def test_unavailable_store_refuses_to_save_rather_than_losing_records(monkeypatch):
    """로컬 파일로 조용히 대체하지 않는다 — 그러면 기록이 사라진다."""
    import pytest

    record_store = store.UnavailableStore('자격 증명이 잘못되었습니다')

    with pytest.raises(RuntimeError, match='자격 증명'):
        record_store.add(student_id='10101 가나다', mode='자리', wpm=100,
                         accuracy=95.0, score=9025, duration_sec=300)

    with pytest.raises(RuntimeError):
        record_store.top('자리')


def test_health_reports_why_it_is_misconfigured(monkeypatch):
    """/health가 원인을 그대로 알려줘야 한다. 이게 없으면 진단할 방법이 없다."""
    import app as app_module

    broken = store.UnavailableStore('FIREBASE_SERVICE_ACCOUNT_JSON이 한 줄 JSON이 아닙니다')
    flask_app = app_module.create_app(record_store=broken)
    flask_app.config.update(TESTING=True)

    response = flask_app.test_client().get('/health')
    payload = response.get_json()

    assert response.status_code == 503
    assert payload['status'] == 'misconfigured'
    assert payload['backend'] == 'unavailable'
    assert any('FIREBASE_SERVICE_ACCOUNT_JSON' in p for p in payload['problems'])


def test_missing_credentials_and_bad_credentials_give_different_advice(monkeypatch):
    """값을 아직 안 넣은 사람에게 "한 줄 JSON인지 확인하세요"는 엉뚱한 안내다."""
    for name in ('FIREBASE_SERVICE_ACCOUNT_JSON', 'FIREBASE_SERVICE_ACCOUNT_FILE',
                 'GOOGLE_APPLICATION_CREDENTIALS'):
        monkeypatch.delenv(name, raising=False)

    assert '설정되어 있지 않습니다' in store._credential_hint()

    monkeypatch.setenv('FIREBASE_SERVICE_ACCOUNT_JSON', '{"type": "service_account"}')
    assert '한 줄 JSON인지' in store._credential_hint()
