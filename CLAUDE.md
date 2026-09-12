# 파이썬 타자 도우미 - 개발 가이드

중학교 1학년 정보 교과용 파이썬 타자 연습 웹 앱. Flask + 바닐라 JS + Firebase Firestore.

## 빠른 시작

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest            # 테스트용

# Firebase 없이 로컬 파일 저장소로 실행 (수업 전 점검용)
STORE_BACKEND=local SESSION_SECRET=dev .venv/bin/python main.py
# http://localhost:5000

# 테스트
STORE_BACKEND=local .venv/bin/python -m pytest -q
```

배포 실행은 `gunicorn --workers 1 --threads 8 main:app` (Procfile 참고).

## 파일 구조

| 파일 | 역할 |
| --- | --- |
| `app.py` | Flask 앱 팩토리(`create_app`)와 모든 라우트 |
| `config.py` | 환경 변수 기반 설정(연습 시간, 부정행위 방지 기준 등) |
| `content.py` | 4개 연습 모드 정의와 연습 텍스트 생성 |
| `scoring.py` | 학번 검증, **점수 계산**, 기록 무결성 검증 |
| `sessions.py` | 연습 세션 추적(키 입력 집계)과 제출 빈도 제한 — **프로세스 메모리** |
| `store.py` | 기록 저장소. Firestore 백엔드 + 로컬 JSON 백엔드 |
| `main.py` | WSGI 엔트리 포인트 |
| `static/js/app.js` | 연습 화면 로직(타이머, 하이라이트, 통계, 저장) |
| `static/js/leaderboard.js` | 홈 화면 명예의 전당 |
| `static/vendor/` | Bootstrap·Bootstrap Icons 사본 (CDN 차단 대비) |
| `tests/` | pytest 테스트 |

## 꼭 기억할 규칙

### 1) 워커는 반드시 1개
`sessions.py`의 연습 세션·키 입력 집계가 프로세스 메모리에 있다. 워커가 2개
이상이면 키 입력을 받은 워커와 저장 요청을 받은 워커가 달라져 "타이핑 세션을
찾을 수 없습니다" 오류가 난다. 동시 접속은 스레드(`--threads`)로 처리한다.
워커를 늘려야 할 규모가 되면 세션 상태를 Firestore나 Redis로 옮겨야 한다.

### 2) 점수와 연습 시간은 서버가 계산한다
- 점수: `scoring.compute_score(wpm, accuracy)` = `round(타수 × (정확도/100)² × 100)`
- 저장되는 `duration_sec`: 항상 `config.PRACTICE_SECONDS`
- 클라이언트가 보낸 `score`·`duration_sec`은 **무시**한다.

화면의 '점수'는 `static/js/app.js`의 `computeScore()`가 같은 공식으로 계산한다.
**한쪽 공식만 바꾸면 학생이 본 점수와 저장된 점수가 달라진다. 항상 같이 바꾼다.**

화면의 '적립 포인트'는 단어를 정확히 완성할 때 쌓이는 재미 요소이고, 서버에
저장되지 않으며 순위와 무관하다.

### 3) 연습 흐름 (라우트 순서)
1. `GET /practice/<mode>` → 1회용 토큰 + session_id 발급, 세션 등록
2. `POST /api/practice/start` → 서버 측 연습 시작 시각 기록
3. `POST /api/keystroke` → 키 입력 수를 약 2초 단위로 묶어서 보고
4. `POST /api/records` → 검증 후 저장, 토큰 폐기(1회용)

### 4) 부정행위 방지 (모두 `config.py`에서 조정 가능)
- `MIN_KEYSTROKES`: 최소 키 입력 수
- `MIN_TYPING_SPAN_SECONDS`: 첫 키와 마지막 키 사이 최소 시간 → 콘솔로 한꺼번에
  주입하면 0에 가까워지므로 걸러진다
- `scoring.validate_wpm_against_keystrokes`: 서버가 센 키 입력 수로 설명할 수 없는
  타수를 거부
- `RateLimiter`: 학번당 제출 빈도 제한. **모든 검증을 통과한 요청에만** 카운트한다
  (형식 오류로 학생이 기회를 잃지 않게 하기 위함)

### 5) 시간대
Firestore에는 UTC로 저장하고, API 응답에서 `+09:00`이 붙은 ISO 문자열로 변환한다
(`store.to_api_dict`). 브라우저는 이 값을 그대로 해석하면 된다.

### 6) 외부 라이브러리는 CDN이 아니라 프로젝트에 포함
학교 네트워크에서 CDN이 막히면 Bootstrap JS가 없어 모달이 안 뜨고 학생이 기록을
저장할 수 없다. `static/vendor/`의 사본을 쓴다. 업데이트 방법은
`static/vendor/README.md` 참고.

## 코드 리뷰 (Codex)

**리뷰 기준은 `AGENTS.md`의 "Review guidelines" 한 곳에만 둔다.** 여기나 워크플로
프롬프트에 복사하면 둘이 어긋난다(점수 공식으로 이미 겪은 문제). 위 "꼭 기억할 규칙"이
바뀌면 `AGENTS.md`의 점검 항목도 같이 고친다.

### 기본: Codex GitHub 앱 연동 (추가 비용 없음)
유료 ChatGPT 플랜에 포함된다. `chatgpt.com/codex` → 설정에서 이 저장소의
**Code review**를 켜고, 원하면 **Automatic reviews**도 켠다. 수동으로는 PR 댓글에
`@codex review`. API 키가 필요 없다.

### 대안: `.github/workflows/codex-review.yml` (API 종량제 과금)
Actions 탭에서 **수동 실행만** 되게 해 두었다. 지정 브랜치와의 차이를 리뷰해 실행
요약에 적는다(수동 실행 버튼은 워크플로가 기본 브랜치에 있어야 보인다).
`OPENAI_API_KEY` 시크릿이 없으면 건너뛰고 경고만 남긴다.

- ⚠️ OpenAI API는 ChatGPT 구독과 **별도 청구**다. 구독에 API 크레딧은 포함되지 않는다.
- `safety-strategy`는 기본값 `drop-sudo`를 유지한다. `unsafe`나 `read-only`로 바꾸면
  `OPENAI_API_KEY`가 프로세스 메모리에서 읽힐 수 있다.
- 외부 기여자가 있는 저장소가 되면 주의: PR이 `AGENTS.md`를 수정해 리뷰를 유도할 수
  있다(프롬프트 인젝션).

## 저장소 백엔드 전환

`STORE_BACKEND` 환경 변수로 결정한다.

- `auto`(기본): Firebase 자격 증명이 있으면 Firestore, 없으면 로컬 JSON
- `firestore`: Firestore 강제
- `local`: 로컬 JSON 강제 (`LOCAL_DB_PATH`, 기본 `data/records.json`)

`/health`가 현재 백엔드와 연결 상태를 알려준다.

## 아직 구현되지 않은 것 (SRD 참고)

- v0.8 학생 검색 (부분 일치)
- v0.9 교사 관리자 모드 (기록 수정/삭제) — 현재 '교사 로그인' 버튼은 안내만 표시
- 문장/문단 모드는 API·로직은 동작하지만 홈 화면에서 '추후 제공'으로 막아둠
