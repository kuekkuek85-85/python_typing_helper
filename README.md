# README – Replit 개발 체크리스트 (Step by Step)

> 목표: 본 README는 **수업 현장 배포 가능한 최소 단위**부터 기능을 점진적으로 붙여 **안정적으로 1.0 출시**하는 것을 돕습니다.
> 기타: 개발하는 과정에서의 AI agent는 모든 과정과 답변을 한국어로 답변하도록 합니다.
> 스택: Flask + HTML/CSS/JS + Supabase(PostgreSQL)

---

## 0) 준비
- Replit 새 프로젝트(Python) 생성
- **Secrets/환경변수** 설정
  - `SUPABASE_URL` = (프로젝트 URL)
  - `SUPABASE_ANON_KEY` = (anon 키)
  - `ADMIN_USER` = `admin`
  - `ADMIN_PASS` = `admin`
  - `SESSION_SECRET` = (랜덤 시크릿 키)
- 패키지 설치
  ```bash
  pip install flask supabase
  ```
- Supabase SQL 콘솔에 아래 테이블/인덱스 실행 (PRD 참조)
  ```sql
  CREATE TABLE IF NOT EXISTS records (
    id SERIAL PRIMARY KEY,
    student_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    wpm INT NOT NULL,
    accuracy FLOAT NOT NULL,
    score INT NOT NULL,
    duration_sec INT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
  );
  CREATE INDEX IF NOT EXISTS idx_records_mode ON records(mode);
  CREATE INDEX IF NOT EXISTS idx_records_sort ON records(score DESC, accuracy DESC, wpm DESC, created_at ASC);
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  CREATE INDEX IF NOT EXISTS idx_records_student_id_trgm ON records USING gin (student_id gin_trgm_ops);
  ```

---

## v0.1 프로젝트 스캐폴드
- [ ] Flask 기본 서버 (`app.py`), 루트 라우트 반환(헬스체크)
- [ ] 정적 폴더 `static/`와 템플릿 `templates/` 구성
- [ ] 홈 페이지: 4개 모드 선택 카드(자리/낱말/문장/문단)

## v0.2 자리 연습 UI + 타이머
- [ ] 자리 연습 화면: 문제 문구, 입력창, 오타 하이라이트
- [ ] 5분 카운트다운 타이머(클라)
- [ ] 5분 이내 **저장 버튼 비활성화**

## v0.3 낱말/문장/문단 모드 추가
- [ ] 각 모드별 예문 세트/로직 분리(난이도 곡선)
- [ ] 문단 모드: 들여쓰기 가이드 표시

## v0.4 성능 지표 계산
- [ ] 실시간 WPM(5자/단어), 정확도(%) 계산
- [ ] 점수 계산: `score = round(max(0, WPM) * (accuracy/100)**2 * 100)`
- [ ] 결과 화면: WPM/Accuracy/Score 표시

## v0.5 Supabase 연동(저장)
- [ ] `POST /api/records` 라우트
- [ ] 본문: `student_id`, `mode`, `wpm`, `accuracy`, `score`, `duration_sec`
- [ ] **유효성 검증(백엔드)**: 정규식 `^\d{5}\s[가-힣]{2,4}$`
- [ ] **시간 검증**: `duration_sec >= 300` 인 경우만 저장
- [ ] 프런트 입력창 placeholder: `"학번 이름 (예: 10218 홍길동)"`

## v0.6 대시보드 Top10
- [ ] `GET /api/records/top?mode=…`
- [ ] 정렬: score desc → accuracy desc → wpm desc → created_at asc
- [ ] Top10 렌더링, 모드 탭 4개

## v0.7 더 보기(페이지네이션)
- [ ] `GET /api/records?mode=…&limit=10&offset=0`
- [ ] "더 보기" 클릭 시 10개씩 추가 로드
- [ ] "전체 보기" 토글 또는 무한 스크롤 선택

## v0.8 검색(부분 일치)
- [ ] 상단 검색 바(2자 이상 입력 시 동작, 디바운스 300ms)
- [ ] `search` 파라미터를 받아 `student_id ilike '%q%'`
- [ ] 검색+페이지네이션 동시 동작

## v0.9 교사 관리자 모드
- [ ] 우측 상단 "교사 로그인" 버튼 → 모달
- [ ] 인증(`ADMIN_USER`/`ADMIN_PASS`) 성공 시 토큰 발급(세션 스토리지)
- [ ] 관리자 전용 UI: 행 단위 **수정/삭제** 버튼
- [ ] `PATCH /api/records/{id}`, `DELETE /api/records/{id}` 구현(토큰 검사)

## v1.0 폴리싱 & 배포
- [ ] 로딩 스켈레톤, 빈 상태 메시지
- [ ] 에러 핸들링(네트워크/검증 실패)
- [ ] 크로스 브라우저(윈도우 크롬/엣지), 화면 확대 125% 검증
- [ ] 수락 테스트 패스(아래 목록)

---

## 실행 가이드(Replit)
- `app.py`에 Flask 서버 작성 후 **Run** 버튼
- 포트는 5000 사용 (외부 접근 가능)
- 장치 보안: 관리자 자격은 환경변수로 유지, 필요시 배포 시점에 변경

---

## 샘플 코드 스니펫

### Flask 서버(요약)
```python
from flask import Flask, request, jsonify
import os, re
from supabase import create_client, Client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ID_RE = re.compile(r"^\d{5}\s[가-힣]{2,4}$")

@app.post("/api/records")
def create_record():
    body = request.json or {}
    student_id = body.get("student_id", "").strip()
    mode = body.get("mode")
    wpm = int(body.get("wpm", 0))
    accuracy = float(body.get("accuracy", 0))
    score = int(body.get("score", 0))
    duration_sec = int(body.get("duration_sec", 0))
    if not ID_RE.match(student_id):
        return jsonify({"error": "형식 오류(예: 10218 홍길동)"}), 400
    if duration_sec < 300:
        return jsonify({"error": "5분 종료 후 저장 가능합니다."}), 400
    res = (supabase.table("records").insert({
        "student_id": student_id,
        "mode": mode,
        "wpm": wpm,
        "accuracy": accuracy,
        "score": score,
        "duration_sec": duration_sec
    }).execute())
    return jsonify({"ok": True, "id": res.data[0]["id"]})
