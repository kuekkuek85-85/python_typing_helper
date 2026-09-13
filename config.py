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

# 클라이언트가 보고한 키 입력 수를 인정하는 최대 속도(초당).
# 브라우저는 개수만 보고하므로 값 자체를 신뢰할 수 없다. 경과 시간으로 설명할 수
# 있는 만큼만 인정해(토큰 버킷) 개발자 도구로 개수를 부풀리지 못하게 한다.
# 400타/분(약 6.7타/초)을 치는 학생도 여유 있게 통과하도록 잡았다.
MAX_KEYSTROKES_PER_SECOND = _env_int("MAX_KEYSTROKES_PER_SECOND", 8)

# 순간적으로 빠르게 치는 구간을 흡수하기 위한 버킷 크기(키 입력 수).
# 이 값이 없으면 잠깐 빠르게 친 정상 기록이 과소 집계되어 거부될 수 있다.
KEYSTROKE_BURST = _env_int("KEYSTROKE_BURST", 80)

# 같은 학번으로 제출할 수 있는 빈도 제한.
RATE_LIMIT_WINDOW = _env_int("RATE_LIMIT_WINDOW", 300)
MAX_SUBMISSIONS_PER_WINDOW = _env_int("MAX_SUBMISSIONS_PER_WINDOW", 3)

# 남은 연습 세션을 정리하는 기준 시간(초).
SESSION_TTL_SECONDS = _env_int("SESSION_TTL_SECONDS", 3 * 3600)

# 브라우저가 키 입력 수를 묶어서 보고하는 간격(밀리초).
# 서버가 정하고 연습 화면에 내려준다(static/js/app.js는 이 값을 그대로 쓴다).
#
# 이 값이 **Firestore 쓰기 횟수를 그대로 결정한다.** 5분 연습 기준으로
# 학생 한 명당 쓰기 횟수 = PRACTICE_SECONDS / (KEYSTROKE_FLUSH_MS/1000).
# 10초면 30회, 2초면 150회다. 한 반 30명이면 각각 900회와 4500회이고,
# Firestore 무료 한도는 하루 2만 회다.
#
# 낮추면 부정행위 판정이 조금 더 촘촘해지지만 쓰기 비용이 그만큼 늘어난다.
# 올릴 때는 KEYSTROKE_BURST를 함께 확인해야 한다 — 한 번에 보고되는 양이
# 버킷 크기를 넘으면 정상 타이핑도 깎인다(sessions.TypingActivity.credit).
KEYSTROKE_FLUSH_MS = _env_int("KEYSTROKE_FLUSH_MS", 10_000)

# --- 연습 세션 저장소 ------------------------------------------------------
# 연습 세션(키 입력 집계)과 제출 빈도 제한을 어디에 둘지 정한다.
#
# "memory"    : 프로세스 메모리. **단일 워커에서만** 동작한다.
# "firestore" : Firestore 문서. 요청마다 프로세스가 달라지는 서버리스에서 쓴다.
# "auto"(기본): 서버리스 환경(Vercel)이 감지되면 firestore, 아니면 memory.
#
# auto가 잘못 고르면 증상이 "타이핑 세션을 찾을 수 없습니다"로만 나타나 원인을
# 찾기 어렵다. 배포 환경에서는 값을 명시하는 편이 안전하다.
SESSION_BACKEND = os.environ.get("SESSION_BACKEND", "auto").strip().lower()

# 서버리스 환경 감지용. Vercel은 런타임에 VERCEL=1을 넣어 준다.
SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

FIRESTORE_SESSION_COLLECTION = os.environ.get(
    "FIRESTORE_SESSION_COLLECTION", "practice_sessions")
FIRESTORE_RATE_LIMIT_COLLECTION = os.environ.get(
    "FIRESTORE_RATE_LIMIT_COLLECTION", "rate_limits")

# 같은 문서에 요청이 겹쳤을 때 트랜잭션을 다시 시도하는 횟수(SDK 기본값은 5).
# 한 학생의 키 입력 보고는 10초 간격이라 원래 겹치지 않지만, 네트워크가 잠시
# 막혔다가 여러 묶음이 한꺼번에 도착하면 경합한다.
FIRESTORE_MAX_ATTEMPTS = _env_int("FIRESTORE_MAX_ATTEMPTS", 12)

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
