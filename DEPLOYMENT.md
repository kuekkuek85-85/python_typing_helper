# 배포 가이드

파이썬 타자 도우미를 Firebase Firestore와 함께 배포하는 방법입니다.

---

## 1. Firebase 준비

1. https://console.firebase.google.com 에서 프로젝트 생성
2. **빌드 → Firestore Database → 데이터베이스 만들기**
   - 위치: `asia-northeast3` (서울) 권장
   - 모드: **프로덕션 모드**로 시작 (아래 보안 규칙을 쓰기 때문에 상관없음)
3. **프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성** → JSON 파일 다운로드
   - ⚠️ 이 파일은 **절대 GitHub에 올리지 않습니다.** (`.gitignore`에 이미 등록)
4. **보안 규칙 적용**: Firestore → 규칙 탭에 `firestore.rules` 내용을 붙여넣고 게시

   이 앱은 서버에서 Admin SDK로만 접근합니다. Admin SDK는 보안 규칙을 우회하므로,
   규칙에서 브라우저의 직접 접근을 전부 막아야 학생이 콘솔로 기록을 위조할 수
   없습니다.

### 색인 (권장, 필수는 아님)

색인 없이도 동작합니다. 다만 만들어 두면 순위표가 전체 문서를 읽지 않고 상위 수십
개만 읽으므로, 기록이 쌓여도 Firestore 비용과 응답 시간이 늘지 않습니다.
**기록이 수백 건을 넘어가면 만드는 것을 권합니다.**

가장 쉬운 방법: 앱을 한 번 실행하면 서버 로그에 아래와 같은 경고가 남고, 그 안의
링크를 누르면 필요한 색인이 미리 채워진 생성 화면이 열립니다.

```
WARNING 상위 문서만 읽는 경로를 쓸 수 없어 모드별 전체 읽기로 대체합니다.
        ... 사유: 400 The query requires an index. You can create it here: https://console.firebase.google.com/...
```

또는 Firebase CLI로: `firebase deploy --only firestore:indexes`
(`firestore.indexes.json` 사용)

---

## 2. 환경 변수

| 이름 | 필수 | 설명 |
| --- | --- | --- |
| `SESSION_SECRET` | ✅ | Flask 세션 서명 키. `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | ✅* | 서비스 계정 JSON 전체를 한 줄로 붙여넣기 |
| `FIREBASE_SERVICE_ACCOUNT_FILE` | ✅* | 또는 키 파일 경로 |
| `FIREBASE_PROJECT_ID` | | 서비스 계정 JSON에 있으면 생략 가능 |
| `SESSION_COOKIE_SECURE` | | HTTPS로 서비스하면 `1` 권장 |
| `STORE_BACKEND` | | `auto`(기본) / `firestore` / `local` |
| `LOG_LEVEL` | | 기본 `INFO` |

\* 둘 중 하나만 설정합니다. Google Cloud Run 같이 **기본 자격 증명(ADC)** 을 쓰는
환경에서는 둘 다 생략해도 됩니다 — 앱이 ADC를 직접 확인해 Firestore를 사용합니다.
배포 후 `/health`의 `backend`가 `firestore`인지 꼭 확인하세요.

연습 규칙·부정행위 방지 기준도 환경 변수로 조정할 수 있습니다. `.env.example`과
`config.py`를 참고하세요.

`SESSION_SECRET`을 설정하지 않으면 앱이 뜰 때 임시 키를 만들고 경고를 남깁니다.
이 경우 서버를 다시 시작할 때마다 진행 중인 연습 세션이 모두 끊깁니다.

---

## 3. ⚠️ 워커는 반드시 1개

연습 세션과 키 입력 집계가 **프로세스 메모리**에 있습니다. 워커를 2개 이상 띄우면
학생이 기록을 저장할 때 "타이핑 세션을 찾을 수 없습니다" 오류가 납니다.

```
gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 60 main:app
```

`Procfile`에 이 설정이 들어 있습니다. 자동 확장(autoscale) 배포도 인스턴스가
여러 개로 늘어나면 같은 문제가 생기니, **최대 인스턴스를 1로 제한**하세요.
한 반(30명) 규모는 단일 인스턴스 + 8스레드로 충분합니다.

---

## 4. 배포 플랫폼

### Render (권장)
1. New → Web Service → GitHub 레포지토리 연결
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 main:app`
4. Environment에 위 환경 변수 등록 (`FIREBASE_SERVICE_ACCOUNT_JSON`은 JSON 한 줄)
5. Instance Count: **1**

### Railway
1. New Project → Deploy from GitHub
2. 환경 변수 등록 후 배포 (Procfile 자동 인식)
3. Replicas: **1**

### Google Cloud Run
1. `gcloud run deploy --source .`
2. 서비스 계정에 Firestore 권한을 주면 `FIREBASE_*` 환경 변수 없이 동작합니다
3. `--max-instances=1` **필수**

### Replit
`.replit`의 run 명령이 이미 `--workers 1 --threads 8`입니다. Secrets에 환경 변수를
등록하면 됩니다.

---

## 5. 배포 후 확인

```bash
curl https://<도메인>/health
# {"status":"healthy","backend":"firestore","database_connected":true}
```

`backend`가 `local`로 나오면 Firebase 자격 증명이 인식되지 않아 로컬 파일 저장소로
동작하는 상태입니다. 대부분의 배포 환경은 디스크가 초기화되므로 **기록이 사라집니다.**
환경 변수를 다시 확인하세요.

그다음 실제 흐름을 한 번 점검합니다.

1. 홈 화면에서 명예의 전당 탭 4개가 보이는지 (Bootstrap이 로드되었다는 뜻)
2. 자리 연습 → '연습 시작' → 한영 키 확인 창이 뜨는지
3. 5분 연습 후 완료 모달이 뜨고, 학번 형식 검증이 동작하는지
4. 저장 후 홈 화면 순위표에 기록이 나타나는지
5. Firebase 콘솔의 `records` 컬렉션에 문서가 생겼는지

---

## 6. 문제 해결

| 증상 | 원인 / 조치 |
| --- | --- |
| `/health`의 `backend`가 `local` | Firebase 환경 변수 누락 또는 JSON 형식 오류. 서버 로그의 "Firestore 초기화 실패" 확인 |
| "타이핑 세션을 찾을 수 없습니다" | 워커/인스턴스가 2개 이상. 1개로 줄이기 |
| "인증 토큰이 일치하지 않습니다" | 연습 페이지를 새로고침하지 않고 오래 열어둔 경우. 다시 연습 시작 |
| 모달·탭이 동작하지 않음 | `static/vendor/` 파일이 배포에 포함됐는지 확인 |
| 저장 버튼이 계속 비활성 | 학번 형식이 `12345 홍길동` (5자리 + 공백 + 한글 2~4자)인지 확인 |
| 정상 기록이 "타이핑 패턴이 비정상입니다"로 거부됨 | `MIN_TYPING_SPAN_SECONDS`를 낮춰보기 (기본 120초) |

---

## 7. 기존 Supabase/PostgreSQL 데이터 이전

v0.8부터 PostgreSQL을 쓰지 않습니다. 기존 `records` 테이블 데이터를 옮기려면
CSV로 내보낸 뒤 Firestore `records` 컬렉션에 같은 필드명
(`student_id`, `mode`, `wpm`, `accuracy`, `score`, `duration_sec`, `created_at`)으로
넣으면 됩니다. `created_at`은 Firestore timestamp(UTC) 또는 ISO 8601 문자열 모두
읽을 수 있습니다.

단, v0.8에서 분당 타수 계산 방식이 바뀌었으므로(배율 보정 제거) 과거 기록과
새 기록의 타수·점수는 직접 비교할 수 없습니다. 순위표를 모드별로 새로 시작하거나,
과거 기록은 참고용으로만 두는 것을 권합니다.
