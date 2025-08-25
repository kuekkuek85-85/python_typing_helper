# 파이썬 타자 도우미 - Railway 배포 가이드

## Railway 배포 방법

### 1. Railway 계정 생성
1. [Railway](https://railway.app/) 사이트 접속
2. GitHub 계정으로 로그인
3. $5 무료 크레딧 제공 (월 500시간 사용 가능)

### 2. 새 프로젝트 생성
1. Railway 대시보드에서 "New Project" 클릭
2. "Deploy from GitHub repo" 선택
3. 이 프로젝트의 GitHub 저장소 선택

### 3. 환경 변수 설정
Railway 프로젝트 설정에서 다음 환경 변수를 추가:

```
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
ADMIN_USER=admin
ADMIN_PASS=admin
SESSION_SECRET=your_random_secret_key
```

### 4. 배포 확인
- Railway가 자동으로 빌드 및 배포 시작
- 배포 완료 후 `yourapp.up.railway.app` 형태의 URL 제공
- 학교 네트워크에서 접속 가능 (표준 HTTPS 443 포트 사용)

## 대안 배포 플랫폼

### PythonAnywhere (교육용 추천)
- 무료 계정: `yourusername.pythonanywhere.com`
- 파이썬 전용 호스팅으로 교육 환경에 최적화
- 웹 콘솔에서 직접 파일 업로드 및 편집 가능

### Render
- 무료 750시간/월
- GitHub 연동 자동 배포
- `yourapp.onrender.com` 도메인

## 학교 네트워크 호환성
- ✅ Railway: 표준 HTTPS (443 포트) - 대부분 학교에서 접속 가능
- ✅ PythonAnywhere: 교육용 도메인, 학교 친화적
- ✅ Render: CDN 사용으로 안정적 접속
- ❌ Heroku: 비표준 포트 사용으로 일부 학교에서 차단

## 배포 후 테스트
1. 홈페이지 접속 확인
2. 각 연습 모드 동작 테스트
3. 점수 저장 및 순위표 확인
4. 관리자 모드 접속 테스트 (admin/admin)