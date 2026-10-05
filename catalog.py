"""교사 대시보드가 바꾸는 설정과 자리 연습 예제 목록.

무엇을 관리하나
- 모드 on/off (자리·낱말·문장·문단): 홈 화면에 무엇을 열어 둘지
- 자리 연습의 **활성 예제 목록**: 어떤 예제 세트를 학생에게 보여줄지
- 「터틀 타이핑 예제」의 DB 백업(원본 마크다운 + 생성한 줄)

왜 DB인가
서버리스(Vercel)는 요청마다 프로세스가 다를 수 있어 메모리에 두면 교사가 바꾼
값이 다른 인스턴스에 반영되지 않는다. 그래서 store.read_config/write_config로
Firestore(자격 증명이 없으면 로컬 JSON)에 저장한다.

기본값은 content.py(코드)에 있고, DB 설정이 그 위에 덮어쓴다. 설정을 못 읽어도
기본값으로 앱이 그대로 돈다.

읽기 비용
설정은 홈·연습 텍스트 요청마다 필요하므로, 프로세스별로 짧게(TTL) 캐시한다.
교사가 바꾼 값은 최대 TTL(기본 30초)만큼 뒤 다른 인스턴스에 퍼진다 — 수업
설정에는 충분하다. 같은 인스턴스에서 교사가 바꾸면 캐시를 바로 비운다.
"""

from __future__ import annotations

import copy
import logging
import threading
import time

import content

logger = logging.getLogger(__name__)

SETTINGS_KEY = 'settings'
SETTINGS_CACHE_TTL_SECONDS = 30

_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, dict]] = {}


def _backup_key(set_id: str) -> str:
    return f'example_backup_{set_id}'


# --- 설정 읽기 ------------------------------------------------------------
def _defaults() -> dict:
    return {
        'modes': {mode: info.get('available', False)
                  for mode, info in content.PRACTICE_MODES.items()},
        'active_example_set': content.DEFAULT_EXAMPLE_SET,
    }


def _merge(defaults: dict, stored: dict | None) -> dict:
    """저장된 설정을 기본값 위에 얹는다. 저장된 값에 없는 항목은 기본값을 쓴다."""
    result = copy.deepcopy(defaults)
    if not isinstance(stored, dict):
        return result

    stored_modes = stored.get('modes')
    if isinstance(stored_modes, dict):
        for mode, available in stored_modes.items():
            if mode in result['modes']:
                result['modes'][mode] = bool(available)

    active = stored.get('active_example_set')
    if active in content.EXAMPLE_SETS:
        result['active_example_set'] = active

    return result


def get_settings(store) -> dict:
    """현재 설정(기본값 + DB 덮어쓰기). 프로세스별로 짧게 캐시한다."""
    now = time.time()
    with _cache_lock:
        entry = _cache.get(SETTINGS_KEY)
        if entry and now - entry[0] < SETTINGS_CACHE_TTL_SECONDS:
            return copy.deepcopy(entry[1])

    try:
        stored = store.read_config(SETTINGS_KEY)
    except Exception as error:  # noqa: BLE001 - 설정을 못 읽어도 기본값으로 돈다
        logger.warning("설정을 읽지 못해 기본값을 씁니다: %s", error)
        stored = None

    settings = _merge(_defaults(), stored)
    with _cache_lock:
        _cache[SETTINGS_KEY] = (now, settings)
    return copy.deepcopy(settings)


def _invalidate() -> None:
    with _cache_lock:
        _cache.pop(SETTINGS_KEY, None)


# --- 파생 조회 ------------------------------------------------------------
def effective_modes(store) -> dict:
    """PRACTICE_MODES에 현재 on/off를 반영한 복사본. 홈 화면 렌더링에 쓴다."""
    settings = get_settings(store)
    modes = copy.deepcopy(content.PRACTICE_MODES)
    for mode, info in modes.items():
        info['available'] = settings['modes'].get(mode, info.get('available', False))
    return modes


def active_example_set_id(store) -> str:
    return get_settings(store)['active_example_set']


def active_example_set(store) -> dict:
    """지금 활성인 예제 세트(없거나 이상하면 기본 세트)."""
    set_id = active_example_set_id(store)
    return content.EXAMPLE_SETS.get(set_id) or content.EXAMPLE_SETS[content.DEFAULT_EXAMPLE_SET]


def active_example_lines(store) -> list[str]:
    """자리 연습이 지금 쓸 예제 줄 목록."""
    return active_example_set(store)['lines']


def active_texts(store, mode: str) -> list[str]:
    """해당 모드가 지금 쓸 후보 텍스트 목록(활성 예제 세트 기준).

    네 모드(자리·문장·문단·낱말) 모두 활성 예제 세트에서 나온다. 교사가
    대시보드에서 예제를 바꾸면 네 모드가 함께 전환된다.
    """
    return content.texts_for_mode(active_example_set(store), mode)


def example_set_choices() -> list[dict]:
    """대시보드 선택지. 코드에 내장된 예제 목록들."""
    return [
        {
            'id': set_id,
            'name': info['name'],
            'description': info.get('description', ''),
            'count': len(info['lines']),
        }
        for set_id, info in content.EXAMPLE_SETS.items()
    ]


# --- 설정 변경(교사 대시보드) ---------------------------------------------
def set_mode_available(store, mode: str, available: bool) -> dict:
    if mode not in content.PRACTICE_MODES:
        raise ValueError(f'알 수 없는 모드입니다: {mode}')

    settings = get_settings(store)
    settings['modes'][mode] = bool(available)
    store.write_config(SETTINGS_KEY, {
        'modes': settings['modes'],
        'active_example_set': settings['active_example_set'],
    })
    _invalidate()
    return settings


def set_active_example_set(store, set_id: str) -> dict:
    if set_id not in content.EXAMPLE_SETS:
        raise ValueError(f'알 수 없는 예제 목록입니다: {set_id}')

    settings = get_settings(store)
    settings['active_example_set'] = set_id
    store.write_config(SETTINGS_KEY, {
        'modes': settings['modes'],
        'active_example_set': set_id,
    })
    _invalidate()
    return settings


# --- 예제 백업 ------------------------------------------------------------
def backup_document(set_id: str = content.DEFAULT_EXAMPLE_SET) -> dict:
    """DB에 백업할 예제 세트 문서(원본 마크다운 + 생성한 줄)."""
    example_set = content.EXAMPLE_SETS[set_id]
    return {
        'id': set_id,
        'name': example_set['name'],
        'source_markdown': example_set.get('source_markdown', ''),
        'lines': list(example_set['lines']),
        'line_count': len(example_set['lines']),
    }


def ensure_backup(store, set_id: str = content.DEFAULT_EXAMPLE_SET) -> bool:
    """예제 백업이 DB에 없으면 만든다. 새로 만들었으면 True.

    있으면 건드리지 않는다(교사가 손댔을 수 있으므로). 자격 증명이 없어 저장할
    수 없으면 조용히 False — 앱 동작에는 지장이 없다.
    """
    try:
        if store.read_config(_backup_key(set_id)):
            return False
        store.write_config(_backup_key(set_id), backup_document(set_id))
        return True
    except Exception as error:  # noqa: BLE001
        logger.warning("예제 백업을 저장하지 못했습니다(%s): %s", set_id, error)
        return False


def ensure_backups(store) -> list[str]:
    """내장 예제 세트를 모두 DB에 백업한다. 새로 만든 세트의 id 목록을 돌려준다."""
    created = []
    for set_id in content.EXAMPLE_SETS:
        if ensure_backup(store, set_id):
            created.append(set_id)
    return created


def read_backup(store, set_id: str = content.DEFAULT_EXAMPLE_SET) -> dict | None:
    try:
        return store.read_config(_backup_key(set_id))
    except Exception as error:  # noqa: BLE001
        logger.warning("예제 백업을 읽지 못했습니다(%s): %s", set_id, error)
        return None
