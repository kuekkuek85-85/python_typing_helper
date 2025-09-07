# PRD – Replit 기반 파이썬 타자 도우미 웹사이트
작성일: 2025-08-18
버전: 1.0
작성자: (정보 교과) 이승엽 교사 팀

---

## 1) 배경 & 목적
- **배경**: 중학교 1학년 학생들은 영문 타자 속도/정확도가 낮아 파이썬 문법 학습에 진입 장벽이 존재함.
- **목적**: ① 영문 타자 숙련, ② 파이썬 핵심 구문/토큰 반복 노출, ③ 5분 집중 연습을 통한 성취감과 몰입 제공.

## 2) 대상 & 환경
- **대상**: 중학교 1학년(프로그래밍 초심자)
- **수업 맥락**: 정보 교과, 파이썬 기초 단원
- **플랫폼/스택**: Replit · Flask(백엔드) · HTML/CSS/JS(프런트) · Supabase(PostgreSQL)
- **로그인 정책(학생)**: 로그인 없음(저장 시 학번+이름만 제출)

## 3) 학습 범위(토큰/키워드)
- **기본 입출력**: `print`, `input`
- **변수/자료형/빌트인**: `int`, `float`, `str`, `bool`, `list`, `type`, `True`, `False`
- **연산자**: 산술 `+ - * / // % **`, 비교 `== != < > <= >=`, 논리 `and or not`
- **제어 구조**: `if`, `elif`, `else`, `for`, `while`, 흐름 제어 `break`, `continue`, `pass`, **콜론 `:`**
- **함수**: `def`, `return`, `global`, `nonlocal`
- **리스트 다루기**: 인덱싱 `[]`, 메서드 `append`, `remove`, `pop`, `sort`, 빌트인 `len`

> 주의: `int`, `list` 등은 **예약어(keyword)** 가 아닌 **빌트인(내장)** 명칭이지만 학습/타자 노출 대상으로 포함.

## 4) 핵심 사용자 스토리
- **학생**: "모드(자리/낱말/문장/문단)를 선택→ 5분 동안 타자 → 시간이 끝나면 결과 확인 → 학번+이름(형식 유효) 입력 → 기록 저장 → 명예의 전당 확인"
- **교사**: "우측 상단 '교사 로그인'(admin/admin) → 관리자 모드 → 기능별 대시보드에서 기록 **검색/확인/수정/삭제**"

## 5) 기능 사양
### 5.1 모드(4단계, 각 5분)
1) **자리 연습**: 홈로우/영문 자판/파이썬에서 자주 쓰는 기호(`:`, `()`, `[]`, `""` 등) 포함  
2) **낱말 연습**: 키워드/빌트인/메서드 단어(`print`, `if`, `append` 등)  
3) **문장 연습**: 짧은 구문(`for i in range(10):`, `print("hi")`)  
4) **문단(코딩 블록)**: 들여쓰기 포함 3~6줄 프로그램
- **타이머**: 진입 즉시 5분(300초) 카운트다운. **종료 후에만 저장 버튼 활성화.**

### 5.2 기록 저장(학생 입력 조건)
- 입력창 placeholder(hint): **"학번 이름 (예: 10218 홍길동)"**
- **유효성(프런트·백엔드 동시 검증)**: `^\d{5}\s[가-힣]{2,4}$`
- 저장 필드: `student_id(문자열)`, `mode`, `wpm`, `accuracy`, `score`, `duration_sec`, `created_at`
- **서버 검증**: `duration_sec < 300` 인 경우 **저장 거부**(조기 종료 방지)

### 5.3 측정/채점
- **WPM**: 표준 5자=1단어, 공백/기호 포함. 실시간 집계.
- **정확도(%)**: (정타 수 / 총 입력 수) × 100
- **스코어**(기본 공식): `score = round(max(0, WPM) * (accuracy/100)**2 * 100)`  
  - 목적: 속도·정확도 동시 반영, 오타 과도 시 점수 하락

### 5.4 명예의 전당(대시보드)
- **표시 기본**: **Top 10** (정렬: `score desc → accuracy desc → wpm desc → created_at asc`)
- **더 보기**: 10개씩 추가 로드(`limit=10&offset=…`), 또는 전체 보기 토글
- **검색**: 상단 검색바(부분 일치, 대소문자 무시) → `student_id` 컬럼 ilike '%q%'
- **뷰 탭**: 자리 / 낱말 / 문장 / 문단
- **관리자 모드 UI**: 각 행에 **수정/삭제** 아이콘 노출

### 5.5 교사 관리자 모드
- **버튼**: 화면 우측 상단 "교사 로그인"
- **자격 증명**: `admin / admin` (환경변수로 변경 가능)
- **권한**: 기능별 대시보드의 기록 **수정(PATCH)/삭제(DELETE)**
- **세션**: 로그인 성공 시 간단 토큰(세션 스토리지) → API 헤더 전송

## 6) 화면 흐름(IA/UX 개요)
- 홈 → 모드 선택 → 연습 화면(문제·입력·타이머·오타 강조) → 결과(속도/정확도/점수) → **학번+이름 입력 폼** → 저장 완료 → 명예의 전당
- 상단 고정 탭: 자리/낱말/문장/문단
- 우측 상단: **교사 로그인** 버튼

## 7) API 사양(Flask)
- `GET /api/records/top?mode={mode}` → Top10, 총합 반환
- `GET /api/records?mode={m}&limit=10&offset=0&search={q}` → 페이지네이션(검색 포함)
- `POST /api/records` → 저장(본문: 측정치 + student_id + mode + duration_sec)  
  - 서버: `student_id` 정규식 검증, `duration_sec >= 300` 검증
- (관리자) `PATCH /api/records/{id}`, `DELETE /api/records/{id}`  
  - 헤더 토큰 필수

## 8) 데이터 모델 & 인덱스(Supabase)
```sql
CREATE TABLE IF NOT EXISTS records (
  id SERIAL PRIMARY KEY,
  student_id TEXT NOT NULL,     -- "10218 홍길동"
  mode TEXT NOT NULL,           -- "자리" | "낱말" | "문장" | "문단"
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
