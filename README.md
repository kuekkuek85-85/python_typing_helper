# 파이썬 타자 도우미 – Replit 개발 체크리스트 (Step by Step)

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
- [x] Flask 기본 서버 (`app.py`), 루트 라우트 반환(헬스체크)
- [x] 정적 폴더 `static/`와 템플릿 `templates/` 구성
- [x] 홈 페이지: 4개 모드 선택 카드(자리/낱말/문장/문단)

## v0.2 자리 연습 UI + 타이머
- [x] 자리 연습 화면: 문제 문구, 입력창, 오타 하이라이트
- [x] 5분 카운트다운 타이머(클라)
- [x] 5분 이내 **저장 버튼 비활성화**

## v0.3 낱말/문장/문단 모드 추가 (완료)
- [x] 각 모드별 예문 세트/로직 분리(난이도 곡선)
- [x] 문단 모드: 들여쓰기 가이드 표시
- [x] **실시간 점수 시스템**: 단어 완성시 즉시 점수 적립하는 게임화 요소 추가

## v0.4 성능 지표 계산 (완료)
- [x] 실시간 WPM(정확한 글자 수 기준, 5자/단어), 정확도(%) 계산
- [x] 점수 계산: `score = round(max(0, WPM) * (accuracy/100)**2 * 100)`
- [x] 결과 화면: WPM/Accuracy/Score 표시
- [x] **WPM 공식 개선**: 정확한 글자 수만 계산하여 현실적인 타수 측정

## v0.5 Supabase 연동(저장) (완료)
- [x] `POST /api/records` 라우트
- [x] 본문: `student_id`, `mode`, `wpm`, `accuracy`, `score`, `duration_sec`
- [x] **유효성 검증(백엔드)**: 정규식 `^\d{5}\s[가-힣]{2,4}$`
- [x] **시간 검증**: `duration_sec >= 300` 인 경우만 저장
- [x] 프런트 입력창 placeholder: `"학번 이름 (예: 10218 홍길동)"`
- [x] **타임스탬프 개선**: 한국 시간(KST) 적용으로 실제 수업시간과 일치

## v0.6 대시보드 Top10 (완료)
- [x] `GET /api/records/top?mode=…`
- [x] 정렬: score desc → accuracy desc → wpm desc → created_at asc
- [x] Top10 렌더링, 모드 탭 4개
- [x] **대시보드 통합**: 별도 페이지 제거하고 홈페이지에 순위표 통합

## v0.7 더 보기(페이지네이션) (완료)
- [x] `GET /api/records?mode=…&limit=10&offset=0`
- [x] "더 보기" 클릭 시 10개씩 추가 로드
- [x] "전체 보기" 토글 또는 무한 스크롤 선택
- [x] **UI 개선**: "Top10 보기"/"전체 보기" 토글 버튼으로 전환 가능
- [x] **스크롤 개선**: 600px 높이 제한으로 깔끔한 인터페이스

## v0.7.1 데이터 품질 개선 (완료)
- [x] **WPM 재계산**: 기존 114개 기록을 새로운 공식으로 일괄 업데이트
- [x] **타임스탬프 통합**: 기존 113개 기록을 UTC에서 한국시간(+9시간)으로 변환
- [x] **API 엔드포인트**: `/api/admin/recalculate-wpm` 대량 데이터 처리 기능 추가
- [x] **데이터 일관성**: 과거/현재/미래 모든 기록이 동일한 기준으로 통일

## v0.7.2 UI/UX 개선 (완료)
- [x] **Shift 키 매핑 개선**: 키보드 자판 위치에 따른 올바른 Shift 키 하이라이팅
- [x] **등수 계산 개선**: 동점자 처리로 공정한 순위 표시 (2등이 2명이면 다음은 4등)
- [x] **키보드 표시 개선**: = 키 위에 + 표시, , 키 위에 < 표시로 정확한 시각화
- [x] **Caps Lock 기능**: 소문자 기본 표시 및 Caps Lock 토글로 대문자 전환
- [x] **한영 전환 지원**: 연습 시작 시 입력 모드 확인 및 한글 입력 방지 기능

## v0.8 검색(부분 일치)
- [ ] 상단 검색 바(2자 이상 입력 시 동작, 디바운스 300ms)
- [ ] `search` 파라미터를 받아 `student_id ilike '%q%'`
- [ ] 검색+페이지네이션 동시 동작

## v0.9 교사 관리자 모드
- [ ] 우측 상단 "교사 로그인" 버튼 → 모달
- [ ] 인증(`ADMIN_USER`/`ADMIN_PASS`) 성공 시 토큰 발급(세션 스토리지)
- [ ] 관리자 전용 UI: 행 단위 **수정/삭제** 버튼
- [ ] `PATCH /api/records/{id}`, `DELETE /api/records/{id}` 구현(토큰 검사)

## v1.0 폴리싱 & 배포 (준비 중)
- [x] **핵심 기능 완성**: 4개 모드, 실시간 성과 측정, 순위표, 데이터 저장
- [x] **데이터 품질**: WPM 공식 개선, 한국시간 타임스탬프, 기존 데이터 일괄 업데이트
- [x] **사용자 경험**: 홈페이지 순위표 통합, Top10/전체보기 토글, 반응형 디자인
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
