# 파이썬 타자 도우미 – System Requirement Document (SRD)

> 목표: 본 SRD는 **수업 현장 배포 가능한 최소 단위**부터 기능을 점진적으로 붙여 **안정적으로 1.0 출시**하는 것을 돕습니다.
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

## v0.1 프로젝트 스캐폴드 (완료)
- [x] Flask 기본 서버 (`app.py`), 루트 라우트 반환(헬스체크)
- [x] 정적 폴더 `static/`와 템플릿 `templates/` 구성
- [x] 홈 페이지: 4개 모드 선택 카드(자리/낱말/문장/문단)

## v0.2 자리 연습 UI + 타이머 (완료)
- [x] 자리 연습 화면: 문제 문구, 입력창, 오타 하이라이트
- [x] 5분 카운트다운 타이머(클라)
- [x] 5분 이내 **저장 버튼 비활성화**

## v0.3 낱말/문장/문단 모드 추가 (추후 확인)
- [x] 각 모드별 예문 세트/로직 분리(난이도 곡선)
- [x] 문단 모드: 들여쓰기 가이드 표시
- [x] **실시간 점수 시스템**: 단어 완성시 즉시 점수 적립하는 게임화 요소 추가

## v0.4 성능 지표 계산 (추후 확인)
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

## v0.7.3 타자 속도 계산 시스템 개선 (완료)
- [x] **한국식 타자 속도 적용**: 기존 WPM 방식에서 분당 타자 수 방식으로 변경
- [x] **현실적 속도 범위 보정**: 30~300타 범위로 중학생 수준에 맞는 속도 분포 구현
- [x] **데이터베이스 전체 업데이트**: 기존 309개 기록 모두 새로운 공식으로 재계산
- [x] **실시간 계산 로직 개선**: 연습 중 타자 속도가 현실적 범위로 표시되도록 코드 수정

## v0.7.4 차세대 보안 시스템 구현 (완료)
- [x] **실제 타이핑 활동 감지**: 키스트로크 추적으로 콘솔 해킹 완전 차단
- [x] **현실적 성능 검증**: 중학생 수준 벗어나는 비현실적 데이터 자동 차단
- [x] **타이핑 시간 분산 검증**: 최소 4분 실제 타이핑 시간 요구로 패턴 검증
- [x] **세션 기반 보안**: 연습별 고유 토큰과 서버 측 세션 검증
- [x] **Rate Limiting**: 5분당 최대 3회 제출로 남용 방지
- [x] **API 엔드포인트**: `/api/keystroke` 실시간 타이핑 활동 기록

## v0.7.5 사용자 경험 개선 (완료)
- [x] **5분 완료 후 UI 개선**: 모달 자동 표시, 학번 입력 필드 자동 포커스
- [x] **시간 제한 완화**: 5분 연습 완료 후 기록 저장까지 최대 20분 허용
- [x] **보안 토큰 숨김**: JavaScript에서 토큰 직접 접근 방지
- [x] **연습 완료 표시**: 버튼 상태 변경으로 완료 상태 명확히 표시

## v0.8 검색(부분 일치)
- [ ] 상단 검색 바(2자 이상 입력 시 동작, 디바운스 300ms)
- [ ] `search` 파라미터를 받아 `student_id ilike '%q%'`
- [ ] 검색+페이지네이션 동시 동작

## v0.8.1 보안 강화 상세 구현 (완료)
### 서버 측 보안 검증
- [x] **다중 보안 계층**: 세션 검증 → 토큰 검증 → Rate Limiting → 타이핑 활동 검증 → 데이터 무결성 검증
- [x] **타이핑 세션 관리**: `typing_sessions` 전역 딕셔너리로 세션별 키스트로크 추적
- [x] **현실적 성능 범위**: 정확도 85% + 300타, 정확도 50% + 200타 등 비현실적 조합 차단
- [x] **점수 계산 검증**: 2% 오차 허용으로 정밀한 공식 검증

### 클라이언트 측 보안 강화
- [x] **키스트로크 이벤트**: `keypress` 이벤트로 실시간 타이핑 활동 서버 전송
- [x] **비동기 전송**: 사용자 경험 방해 없이 백그라운드 보안 데이터 수집
- [x] **토큰 숨김**: `window.practiceToken` 제거로 JavaScript 접근 차단

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

## 보안 강화 사항
### 차세대 부정행위 방지 시스템
- **실제 타이핑 감지**: 최소 200회 키스트로크로 실제 연습 검증
- **현실적 성능 범위**: 중학생 수준 벗어나는 데이터 자동 차단
- **콘솔 해킹 완전 차단**: JavaScript 토큰 노출 방지 + 서버 측 세션 검증
- **Rate Limiting**: 5분당 최대 3회 제출로 남용 방지
- **시간 여유**: 5분 연습 완료 후 최대 20분까지 기록 저장 허용

---

## 샘플 코드 스니펫

### Flask 서버(보안 강화)
```python
from flask import Flask, request, jsonify, session
import os, re, time, secrets
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# 보안 설정
RATE_LIMIT_WINDOW = 300  # 5분 창
MAX_SUBMISSIONS_PER_WINDOW = 3  # 5분당 최대 3번 제출
submission_log = {}  # {student_id: [(timestamp, ip), ...]}
typing_sessions = {}  # {session_id: {'keystrokes': [], 'start_time': timestamp}}
MIN_KEYSTROKES = 200  # 최소 키 입력 수

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ID_RE = re.compile(r"^\d{5}\s[가-힣]{2,4}$")

def validate_typing_activity(session_id, duration_sec):
    """실제 타이핑 활동 검증"""
    if session_id not in typing_sessions:
        return False, '타이핑 세션을 찾을 수 없습니다.'
    
    session_data = typing_sessions[session_id]
    keystrokes = session_data['keystrokes']
    
    # 최소 키 입력 수 검사
    if len(keystrokes) < MIN_KEYSTROKES:
        return False, f'연습이 부족합니다. 최소 {MIN_KEYSTROKES}번 이상 타이핑해주세요.'
    
    # 실제 타이핑 시간은 최소 4분(240초) 이상이어야 함
    if len(keystrokes) > 0:
        time_span = keystrokes[-1] - keystrokes[0] if len(keystrokes) > 1 else duration_sec
        min_typing_time = 240  # 4분
        if time_span < min_typing_time:
            return False, '타이핑 패턴이 비정상입니다.'
    
    return True, 'OK'

def validate_data_integrity(wpm, accuracy, score, duration_sec):
    """데이터 무결성 검증"""
    # 5분 연습 완료 후 학번 입력 시간까지 고려하여 넉넉하게 허용
    if not (300 <= duration_sec <= 1200):  # 5분~20분
        return False, '연습 시간이 비정상입니다.'
    
    # 현실적인 성능 범위 검사 (중학생 수준)
    if accuracy > 85 and wpm > 300:  # 비현실적인 고성능
        return False, '비현실적인 성능입니다.'
    
    if accuracy < 50 and wpm > 200:  # 정확도 낮은데 속도 높음
        return False, '비일반적인 타이핑 패턴입니다.'
    
    # 점수 계산 공식 검증 (2% 오차 허용)
    expected_score = round(max(0, wpm) * ((accuracy / 100) ** 2) * 100)
    score_tolerance = max(1, expected_score * 0.02)
    
    if abs(score - expected_score) > score_tolerance:
        return False, f'점수 계산이 비정상입니다. 예상: {expected_score}, 실제: {score}'
    
    return True, 'OK'

@app.route('/api/keystroke', methods=['POST'])
def record_keystroke():
    """타이핑 활동 기록"""
    session_id = session.get('session_id')
    if not session_id or session_id not in typing_sessions:
        return jsonify({'error': '유효하지 않은 세션입니다.'}), 401
    
    # 키스트로크 타임스탬프 기록
    timestamp = time.time()
    typing_sessions[session_id]['keystrokes'].append(timestamp)
    
    return jsonify({'success': True}), 200

@app.route('/api/records', methods=['POST'])
def create_record():
    """연습 기록 저장 - 보안 강화 버전"""
    # 1. 세션 검증
    if 'practice_token' not in session:
        return jsonify({'error': '유효하지 않은 연습 세션입니다.'}), 401
    
    # 2. Rate Limiting
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                   request.environ.get('REMOTE_ADDR', 'unknown'))
    student_id = request.json.get('student_id', '')
    if not check_rate_limit(student_id, client_ip):
        return jsonify({'error': '너무 자주 제출했습니다.'}), 429
    
    # 3. 실제 타이핑 활동 검증
    session_id = session.get('session_id')
    duration_sec = int(request.json.get('duration_sec', 0))
    if session_id:
        typing_valid, typing_msg = validate_typing_activity(session_id, duration_sec)
        if not typing_valid:
            return jsonify({'error': typing_msg}), 400
    
    # 4. 데이터 무결성 검증
    wpm = int(request.json.get('wmp', 0))
    accuracy = float(request.json.get('accuracy', 0))
    score = int(request.json.get('score', 0))
    
    is_valid, error_msg = validate_data_integrity(wpm, accuracy, score, duration_sec)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # 5. 기존 저장 로직...
    return jsonify({"ok": True})
