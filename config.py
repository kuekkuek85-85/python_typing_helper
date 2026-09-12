"""환경 변수 기반 애플리케이션 설정.

모든 설정은 환경 변수로 덮어쓸 수 있고, 값이 없거나 잘못된 형식이면
안전한 기본값을 사용한다. (.env.example 참고)
"""

import logging
import os

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("환경 변수 %s 값(%r)이 정수가 아니어서 기본값 %s를 사용합니다.", name, raw, default)
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- 연습 규칙 -------------------------------------------------------------
# 한 번의 연습 길이(초). 클라이언트 타이머와 서버 검증이 이 값을 공유한다.
PRACTICE_SECONDS = _env_int("PRACTICE_SECONDS", 300)

# 연습이 끝난 뒤 학번/이름을 입력해 저장할 수 있는 여유 시간(초).
SAVE_GRACE_SECONDS = _env_int("SAVE_GRACE_SECONDS", 1200)

# --- 부정행위 방지 ---------------------------------------------------------
# 기록을 인정하기 위한 최소 키 입력 횟수.
MIN_KEYSTROKES = _env_int("MIN_KEYSTROKES", 100)

# 첫 키 입력과 마지막 키 입력 사이에 최소로 필요한 시간(초).
# 콘솔로 키 입력을 한꺼번에 주입하면 이 값이 0에 가까워지므로 부정행위를 걸러낸다.
# 원래 기준은 4분(240초)이었지만, 연습을 일찍 끝내거나 중간에 쉰 학생의 정상 기록까지
# 거부되는 문제가 있어 2분으로 낮췄다.
MIN_TYPING_SPAN_SECONDS = _env_int("MIN_TYPING_SPAN_SECONDS", 120)

# 같은 학번으로 제출할 수 있는 빈도 제한.
RATE_LIMIT_WINDOW = _env_int("RATE_LIMIT_WINDOW", 300)
MAX_SUBMISSIONS_PER_WINDOW = _env_int("MAX_SUBMISSIONS_PER_WINDOW", 3)

# 메모리에 남은 연습 세션을 정리하는 기준 시간(초).
SESSION_TTL_SECONDS = _env_int("SESSION_TTL_SECONDS", 3 * 3600)

# --- 저장소 ---------------------------------------------------------------
# "auto"  : Firebase 자격 증명이 있으면 Firestore, 없으면 로컬 JSON 파일
# "firestore" : Firestore 강제(자격 증명이 없으면 시작 시 실패)
# "local" : 로컬 JSON 파일 강제(테스트/오프라인 수업용)
STORE_BACKEND = os.environ.get("STORE_BACKEND", "auto").strip().lower()

FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "records")

# 목록 조회 결과를 잠시 재사용해 Firestore 읽기 횟수를 줄인다(초).
STORE_CACHE_TTL_SECONDS = _env_int("STORE_CACHE_TTL_SECONDS", 20)

LOCAL_DB_PATH = os.environ.get("LOCAL_DB_PATH", os.path.join("data", "records.json"))

# --- 웹 서버 -------------------------------------------------------------
# HTTPS로 서비스할 때 True로 두면 세션 쿠키가 HTTPS에서만 전송된다.
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)

# 목록 API가 한 번에 돌려줄 수 있는 최대 개수.
MAX_PAGE_SIZE = _env_int("MAX_PAGE_SIZE", 2000)
