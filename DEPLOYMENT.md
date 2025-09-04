# GitHub 배포 가이드

이 문서는 파이썬 타자 도우미를 GitHub을 통해 다양한 플랫폼에 배포하는 방법을 설명합니다.

## 1. 프로젝트 GitHub으로 내보내기

### 방법 1: Git을 통한 내보내기
```bash
# 현재 디렉토리에서 Git 초기화
git init
git add .
git commit -m "Initial commit - Python Typing Helper"

# GitHub 레포지토리 생성 후 연결
git remote add origin https://github.com/[USERNAME]/python-typing-helper.git
git push -u origin main
```

### 방법 2: ZIP 다운로드 후 GitHub 업로드
1. Replit 프로젝트 파일들을 ZIP으로 다운로드
2. GitHub에서 새 레포지토리 생성
3. 파일들을 업로드하여 레포지토리 구성

## 2. 배포 플랫폼 옵션

### A. Heroku (추천)
1. Heroku 계정 생성: https://heroku.com
2. 새 앱 생성
3. GitHub 레포지토리 연결
4. 환경변수 설정 (아래 참조)
5. 자동 배포 활성화

### B. Render
1. Render 계정 생성: https://render.com
2. New Web Service 선택
3. GitHub 레포지토리 연결
4. 빌드 명령: `pip install -r requirements.txt`
5. 시작 명령: `gunicorn --bind 0.0.0.0:$PORT main:app`

### C. Railway
1. Railway 계정 생성: https://railway.app
2. New Project > Deploy from GitHub
3. 레포지토리 선택
4. 환경변수 설정

### D. PythonAnywhere
1. PythonAnywhere 계정 생성: https://pythonanywhere.com
2. Bash console에서 git clone
3. Web app 설정에서 Flask 앱 연결

## 3. 필수 환경변수 설정

배포 플랫폼에서 다음 환경변수들을 설정해야 합니다:

```
DATABASE_URL=postgresql://[USERNAME]:[PASSWORD]@[HOST]:[PORT]/[DATABASE]
SESSION_SECRET=your-random-secret-key
ADMIN_USER=admin
ADMIN_PASS=your-admin-password
```

### Supabase 데이터베이스 URL 가져오기
1. Supabase 대시보드: https://supabase.com/dashboard
2. 프로젝트 선택 > Settings > Database
3. Connection string > Transaction pooler 복사
4. `[YOUR-PASSWORD]`를 실제 비밀번호로 교체

## 4. requirements.txt 생성 (필요시)

pyproject.toml 대신 requirements.txt가 필요한 플랫폼의 경우:

```
email-validator>=2.2.0
flask>=3.1.1
flask-sqlalchemy>=3.1.1
gunicorn>=23.0.0
psycopg2-binary>=2.9.10
pytz>=2025.2
sqlalchemy>=2.0.43
supabase>=2.18.1
werkzeug>=3.1.3
```

## 5. 주의사항

- **데이터베이스**: 현재 Supabase PostgreSQL을 사용하므로 별도 설정 불필요
- **포트 설정**: Procfile에서 `$PORT` 환경변수 사용 (플랫폼에서 자동 할당)
- **HTTPS**: 대부분의 플랫폼에서 자동으로 HTTPS 제공
- **도메인**: 배포 후 플랫폼에서 제공하는 도메인 사용 가능

## 6. 배포 후 확인사항

1. 웹사이트 접속 확인
2. 데이터베이스 연결 확인 (관리자 페이지에서 기록 조회)
3. 모든 기능 테스트 (타자 연습, 기록 저장, 리더보드)
4. 모바일 호환성 확인

## 7. 문제 해결

### 데이터베이스 연결 오류
- DATABASE_URL 환경변수 확인
- Supabase 프로젝트 상태 확인
- 네트워크 연결 허용 설정 확인

### 앱 시작 오류
- Procfile 경로 확인 (`main:app`)
- requirements.txt 의존성 확인
- 로그 확인하여 오류 메시지 분석

## 8. 추가 최적화

### 정적 파일 CDN
- CSS, JS, 이미지 파일을 CDN으로 호스팅하여 성능 향상

### 캐싱
- Flask-Caching 추가하여 데이터베이스 쿼리 최적화

### 모니터링
- 배포 플랫폼의 모니터링 도구 활용
- 에러 로그 추적 설정