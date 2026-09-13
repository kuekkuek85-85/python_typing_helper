# Overview

This project is "파이썬 타자 도우미" (Python Typing Helper) — a Python typing practice web
application designed for middle school students learning Python programming. The
application helps students improve their English typing skills while becoming familiar
with Python syntax, keywords, and common programming patterns. It features four
progressive practice modes (keyboard positions, words, sentences, and code blocks) with
5-minute timed sessions, real-time typing speed and accuracy tracking, and a leaderboard.

> 이 문서는 Replit 시절부터 유지해 온 프로젝트 개요입니다.
> **개발·배포 방법은 [CLAUDE.md](CLAUDE.md)와 [DEPLOYMENT.md](DEPLOYMENT.md)를 보세요.**

## Current Implementation Status (v0.8.0)

Replit + Supabase(PostgreSQL) 환경에서 Claude Code + Firebase(Firestore) 환경으로
이전하고 전체 코드를 정리한 버전입니다.

- ✅ Flask 웹 애플리케이션 (Firebase Firestore 저장)
- ✅ 4개 연습 모드와 동적 텍스트 로딩
- ✅ 실시간 타이핑 검증 및 시각 피드백
- ✅ 5분 타이머, 종료 후에만 저장 허용
- ✅ 한국식 분당 타수(실측값), 정확도, 점수 계산
- ✅ **점수·연습 시간 서버 계산** (클라이언트 값 무시)
- ✅ 단어 완성 시 쌓이는 '적립 포인트' (재미 요소, 순위와 무관)
- ✅ Top10 / 전체 보기 토글이 있는 통합 순위표
- ✅ 동점자 처리 순위 계산
- ✅ 가상 키보드, 다음 키 강조, Caps Lock, 한/영 입력 안내
- ✅ 서버 측 부정행위 방지 (연습 시간·키 입력 수 검증, 1회용 토큰, 제출 빈도 제한)
- ✅ Bootstrap 사본 포함 (CDN 차단 환경 대응)
- ✅ pytest 테스트 (저장소·점수·API·Firestore 로직)

미구현 항목은 [SRD.md](SRD.md)의 v0.8 / v0.9 항목을 참고하세요.

# User Preferences

Preferred communication style: Simple, everyday language.

AI agent 응답은 한국어로 작성합니다.

Work Process: Always explain the plan first before implementing any changes. Wait for
user approval before proceeding with any tasks or modifications.

# System Architecture

## Frontend Architecture
- **Technology Stack**: HTML5, CSS3, JavaScript (vanilla), Bootstrap 5 (dark theme)
- **Assets**: Bootstrap과 Bootstrap Icons를 `static/vendor/`에 포함 — 학교 네트워크에서
  CDN이 막혀도 모달·탭이 동작해야 하기 때문
- **Real-time Features**: 클라이언트 타이머, 실시간 타수/정확도 계산, 글자 단위 검증
- **Responsive Design**: Bootstrap 그리드 기반, 교실 태블릿/노트북 대응

## Backend Architecture
- **Web Framework**: Flask (`create_app` 팩토리 + 세션 관리)
- **API Design**: 연습 텍스트, 연습 시작/키 입력 보고, 기록 저장·조회 REST 엔드포인트
- **Data Validation**: 학번 형식(5자리 + 한글 이름)을 클라이언트·서버 양쪽에서 검증
- **Business Logic**: 분당 타수(정타 수 / 경과 분), 정확도, 점수 계산은 서버가 최종 결정
- **Process State**: 연습 세션·키 입력 집계는 `SESSION_BACKEND`에 따라 프로세스
  메모리 또는 Firestore. 메모리일 때는 **워커 1개 필수**, Firestore면 제약 없음

## Practice Content Management
- **Content Structure**: 난이도별 4개 모드 (`content.py`)
- **Text Generation**: '자리'는 키워드/기호 풀에서 무작위 생성, 나머지는 예문 배열
- **Repeat Avoidance**: 직전에 나온 텍스트는 연속으로 다시 주지 않음

## Scoring and Analytics
- **Score Formula**: `score = round(max(0, 분당 타수) * (정확도/100)^2 * 100)`
  - `scoring.compute_score()`(서버)와 `app.js`의 `computeScore()`(화면)가 동일
- **Ranking**: score desc → accuracy desc → wpm desc → created_at asc
- **Session Tracking**: 서버 측 연습 시작 시각, 키 입력 수·구간 검증

# External Dependencies

## Database Integration
- **Primary Database**: Firebase Firestore (firebase-admin, Admin SDK)
- **Collection**: `records` — `student_id`, `mode`, `wpm`, `accuracy`, `score`,
  `duration_sec`, `created_at`
- **Security Rules**: 브라우저 직접 접근 전면 차단 (`firestore.rules`)
- **Fallback**: 자격 증명이 없으면 로컬 JSON 파일(`data/records.json`)로 자동 전환 —
  Firebase 설정 없이 수업 전 점검·자동 테스트 가능
- **Sorting**: 모드별 조회는 Firestore, 정렬은 서버(복합 색인 불필요)

## Third-party Services
- **Hosting**: Render / Railway / Cloud Run / Replit (DEPLOYMENT.md 참고)
- **CSS Framework**: Bootstrap 5.3.8 + Bootstrap Icons 1.13.1 (프로젝트에 포함)

## Environment Configuration
- **Required Secrets**: `SESSION_SECRET`, `FIREBASE_SERVICE_ACCOUNT_JSON`
  (또는 `FIREBASE_SERVICE_ACCOUNT_FILE`)
- **Optional**: `.env.example` / `config.py` 참고
