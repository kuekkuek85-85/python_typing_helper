"""저장소(정렬·페이지네이션·통계) 테스트."""

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


def test_stats_across_modes(record_store):
    _add(record_store, '10401 가나다', mode='자리', wpm=100, accuracy=90.0)
    _add(record_store, '10401 가나다', mode='낱말', wpm=200, accuracy=100.0)
    _add(record_store, '10402 라마바', mode='자리', wpm=300, accuracy=80.0)

    stats = record_store.stats()
    assert stats['total_records'] == 3
    assert stats['total_students'] == 2
    assert stats['avg_wpm'] == 200.0
    assert stats['avg_accuracy'] == 90.0


def test_stats_on_empty_store(record_store):
    stats = record_store.stats()
    assert stats == {
        'total_students': 0,
        'total_records': 0,
        'avg_wpm': 0.0,
        'avg_accuracy': 0.0,
    }


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
