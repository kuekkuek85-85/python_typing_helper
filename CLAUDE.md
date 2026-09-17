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
| `sessions.py` | 연습 세션 추적(키 입력 집계)과 제출 빈도 제한. 메모리 / Firestore 백엔드 |
| `store.py` | 기록 저장소. Firestore 백엔드 + 로컬 JSON 백엔드 |
| `main.py` | WSGI 엔트리 포인트 (`gunicorn main:app`). Vercel은 `app.py`의 `app`을 직접 찾는다 |
| `static/js/app.js` | 연습 화면 로직(타이머, 하이라이트, 통계, 저장) |
| `static/js/leaderboard.js` | 홈 화면 명예의 전당 |
| `static/vendor/` | Bootstrap·Bootstrap Icons 사본 (CDN 차단 대비) |
| `tests/` | pytest 테스트 |

## 꼭 기억할 규칙

### 1) 연습 세션은 요청 사이에 이어져야 한다
5분 연습 한 번은 **약 33개의 요청**으로 이루어지고(시작 1 + 키 입력 보고 30여 개 +
저장 1), 이들이 같은 집계를 보아야 저장이 된다. 그 집계를 어디에 두는지가
`config.SESSION_BACKEND`다.

- `memory`: 프로세스 메모리(`sessions.TypingSessionRegistry`). 빠르고 공짜지만
  **워커/인스턴스가 1개일 때만** 동작한다. 동시 접속은 스레드로 처리한다.
- `firestore`: Firestore 문서(`sessions.FirestoreSessionRegistry`). 서버리스
  (Vercel)용. 인스턴스가 몇 개로 늘어나도 된다.
- `auto`(기본): `config.SERVERLESS`가 참이면 firestore, 아니면 memory.

잘못 고르면 증상은 하나다 — 저장할 때 "타이핑 세션을 찾을 수 없습니다".
`/health`의 `session_backend`로 확인한다.

**두 백엔드는 상태 전이 함수(`_apply_start`, `_apply_keystrokes`)를 공유한다.**
부정행위 방지 규칙이 백엔드마다 달라지면 안 되기 때문이다. 규칙을 고칠 때는
그 함수만 고치고, 백엔드는 건드리지 않는다.

토큰 버킷은 읽고-고쳐-쓰는 연산이라 Firestore 백엔드에서는 **트랜잭션**으로
감싼다(`sessions._mutate_document`). 이걸 빼면 동시에 도착한 두 요청이 서로의
차감을 덮어써 인정량이 부풀 수 있다.

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
3. `POST /api/keystroke` → 키 입력 수를 `config.KEYSTROKE_FLUSH_MS`(기본 10초)
   단위로 묶어서 보고. 이 간격은 서버가 정해 연습 화면에 내려준다
   (`window.keystrokeFlushMs`). Firestore 백엔드에서는 **이 간격이 곧 쓰기
   횟수**이므로 줄이기 전에 DEPLOYMENT.md의 비용 계산을 먼저 본다.
4. `POST /api/records` → 검증 후 저장, 토큰 폐기(1회용)

### 4) 부정행위 방지 (모두 `config.py`에서 조정 가능)
- `MIN_KEYSTROKES`: 최소 키 입력 수
- `MIN_TYPING_SPAN_SECONDS`: 첫 키와 마지막 키 사이 최소 시간 → 콘솔로 한꺼번에
  주입하면 0에 가까워지므로 걸러진다
- `MAX_KEYSTROKES_PER_SECOND` / `KEYSTROKE_BURST`: 브라우저가 보고한 키 입력 수를
  **경과 시간으로 설명 가능한 만큼만** 인정하는 토큰 버킷(`sessions.TypingActivity.credit`).
  개수를 부풀려 보고해도 인정되지 않는다.
- `scoring.validate_wpm_against_keystrokes`: 서버가 인정한 키 입력 수로 설명할 수 없는
  타수를 거부. **정타 수는 총 키 입력 수를 넘을 수 없으므로 배율은 1에 가까워야 한다.**
  배율을 키우면 키 입력을 조금만 보고하고 높은 타수를 주장할 수 있다.
- `RateLimiter`: 학번당 제출 빈도 제한. **모든 검증을 통과한 요청에만** 카운트한다
  (형식 오류로 학생이 기회를 잃지 않게 하기 위함)

**남아 있는 한계 (알고 쓰는 것):** 서버는 학생이 무엇을 입력했는지 모르고 개수만
받으므로, 개발자 도구를 쓸 줄 아는 학생은 연습 시간 내내 요청을 보내며
`scoring.HIGH_ACCURACY_MAX_WPM`(=400타) × 정확도 100% 에 해당하는 점수까지는
위조할 수 있다. 즉 **완벽한 사람이 낼 수 있는 최고점과 같은 수준까지**이며 그것을
넘지는 못한다. 이 상한을 더 낮추면 위조 가능 점수도 낮아지지만, 실제로 빠른 학생의
정상 기록이 거부될 위험이 커진다 — 학생들의 실제 타수 분포를 보고 결정할 일이다.
완전히 막으려면 서버가 입력 내용까지 받아 지표를 직접 계산해야 하는데, 그러면
학생이 정답 텍스트를 그대로 되돌려 보낼 수 있어 그것만으로도 충분하지 않다.

### 5) 시간대
Firestore에는 UTC로 저장하고, API 응답에서 `+09:00`이 붙은 ISO 문자열로 변환한다
(`store.to_api_dict`). 브라우저는 이 값을 그대로 해석하면 된다.

### 6) 파이썬 버전은 `.python-version` 한 곳에서 정한다
로컬·CI(`python-version-file`)·**Vercel 빌드**가 모두 이 파일을 읽는다.

Vercel은 `uv.lock`이 있으면 `pip` 대신 `uv sync --frozen`으로 설치하는데,
**uv가 `.python-version`을 그대로 읽는다.** 거기 적힌 버전이 배포 환경에 없으면
빌드가 몇 초 만에 죽는다(`No interpreter found for Python 3.11`). Vercel 자신은
"무시한다"고 경고만 남기므로 로그를 끝까지 봐야 원인이 보인다.

**`pyproject.toml`의 `requires-python`과 함께 고친다** — 테스트가 정합성을 고정한다.

한 가지 알고 쓰는 어긋남: CI는 `requirements.txt`(느슨한 `>=`)로 설치하고
Vercel은 `uv.lock`(고정 버전)으로 설치한다. 둘이 벌어지면 CI가 통과한 조합과
운영이 도는 조합이 달라질 수 있다.

### 7) 외부 라이브러리는 CDN이 아니라 프로젝트에 포함
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

`auto`의 자격 증명 판단은 환경 변수뿐 아니라 **기본 자격 증명(ADC)** 도 확인한다
(`store.firebase_credentials_available`). Cloud Run처럼 서비스 계정이 런타임에
주어지는 환경에서 이걸 놓치면 로컬 JSON으로 조용히 전환되고, 컨테이너가 재시작될 때
학생 기록이 사라진다. **`/health`의 `backend`가 `local`로 나오면 기록이 사라지는
상태**이므로 배포 후 반드시 확인한다.

### Firestore 읽기 양
모드별 조회는 다음 순서로 읽는 양을 줄인다(`store.py`).

- 개수(탭 배지, 페이지네이션 total): **집계 쿼리**(`count()`) — 문서를 읽지 않는다
- Top10·앞쪽 페이지: `order_by(score desc).limit(...)` 로 상위 수십 개만 읽는다.
  복합 색인이 없으면 경고를 한 번 남기고 모드별 전체 읽기로 대체하므로 색인 없이도
  동작한다. 경고 로그에 **색인 생성 링크가 그대로 포함**되니 그걸 누르면 된다.
- 전체 보기: 어차피 전부 필요하므로 모드별 전체 읽기

`records_for_mode`의 결과와 `head`/`count` 파생 캐시는 `STORE_CACHE_TTL_SECONDS`
동안 재사용되고, 기록을 저장하면 해당 모드의 캐시가 모두 무효화된다.

## 아직 구현되지 않은 것 (SRD 참고)

- v0.8 학생 검색 (부분 일치)
- v0.9 교사 관리자 모드 (기록 수정/삭제) — 현재 '교사 로그인' 버튼은 안내만 표시
- 문장/문단 모드는 API·로직은 동작하지만 홈 화면에서 '추후 제공'으로 막아둠
