# 파이썬 타자 도우미 (GitHub Pages)

중학교 1학년을 위한 파이썬 프로그래밍 타자연습 정적 웹사이트입니다.

## 🚀 GitHub Pages 배포 가이드

### 1단계: Supabase 설정
1. [Supabase](https://supabase.com) 가입 및 새 프로젝트 생성
2. Database → SQL Editor에서 다음 테이블 생성:

```sql
CREATE TABLE records (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    mode VARCHAR(10) NOT NULL,
    wpm INTEGER NOT NULL,
    accuracy DECIMAL(5,2) NOT NULL,
    score INTEGER NOT NULL,
    duration_sec INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_records_mode_score ON records(mode, score DESC);
CREATE INDEX idx_records_student_id ON records(student_id);
```

3. Settings → API에서 URL과 anon key 복사

### 2단계: 설정 파일 수정
`static/js/config.js` 파일에서 Supabase 설정 업데이트:

```javascript
const SUPABASE_CONFIG = {
    url: 'https://your-project-ref.supabase.co',
    key: 'your-anon-key-here'
};
```

### 3단계: GitHub Pages 배포
1. GitHub 리포지토리에 코드 푸시
2. Settings → Pages에서 Source를 "Deploy from a branch" 선택
3. Branch를 "main"으로 설정하고 폴더는 "/ (root)" 선택
4. Save 클릭

### 4단계: 접속 확인
`https://username.github.io/repository-name` 으로 접속하여 동작 확인

## 📁 프로젝트 구조

```
/
├── index.html          # 메인 페이지
├── practice.html       # 연습 페이지
├── static/
│   ├── css/
│   │   └── custom.css  # 사용자 정의 스타일
│   └── js/
│       ├── config.js   # 설정 및 상수
│       ├── database.js # Supabase 연결
│       ├── main.js     # 메인 페이지 로직
│       └── practice.js # 연습 페이지 로직
└── README.md
```

## 🎯 기능

- **4가지 연습 모드**: 자리, 낱말, 문장, 문단 (현재 자리 연습만 활성화)
- **실시간 통계**: 분당 타수, 정확도, 점수 계산
- **5분 타이머**: 완주 후에만 결과 저장 가능
- **명예의 전당**: 모드별 순위표 (Top10/전체 보기)
- **가상 키보드**: 다음 키 하이라이트 및 시각적 피드백
- **학생 기록 관리**: 학번+이름 형식으로 개인 기록 저장

## ⚙️ 기술 스택

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Bootstrap 5 (Dark Theme)
- **Database**: Supabase (PostgreSQL)
- **Hosting**: GitHub Pages (정적 사이트)

## 🔧 관리자 기능

- 사용자명: `admin`
- 비밀번호: `admin`

(현재 로그인만 구현, 추가 관리 기능은 향후 버전에서 제공)

## 📱 모바일 지원

반응형 디자인으로 태블릿 및 모바일에서도 사용 가능합니다.

## 🏫 교육용 설정

- **대상**: 중학교 1학년 정보 교과
- **목표**: 파이썬 프로그래밍 타이핑 실력 향상
- **시간**: 5분 세션으로 구성된 체계적 연습

## 🐛 문제 해결

### 데이터베이스 연결 안됨
- `config.js`에서 Supabase URL과 키가 올바른지 확인
- 브라우저 개발자 도구 Console에서 에러 메시지 확인

### 기록이 저장되지 않음
- 5분 완주 후에만 저장 가능
- 학번 형식 확인: "12345 홍길동" (5자리 숫자 + 공백 + 한글 이름)

### GitHub Pages에서 404 에러
- 리포지토리 Settings → Pages 설정 확인
- `index.html` 파일이 루트 디렉토리에 있는지 확인

---

**업데이트**: 2025년 9월 - Flask에서 GitHub Pages로 전환 완료