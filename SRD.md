# 파이썬 타자 도우미 – System Requirement Document (SRD)

> 목표: 본 SRD는 **수업 현장 배포 가능한 최소 단위**부터 기능을 점진적으로 붙여 **안정적으로 1.0 출시**하는 것을 돕습니다.
> 기타: 개발하는 과정에서의 AI agent는 모든 과정과 답변을 한국어로 답변하도록 합니다.
> 스택: 정적 HTML/CSS/JS + Supabase JavaScript SDK + GitHub Pages

---

## 0) 준비
- GitHub 리포지토리 생성
- **Supabase 설정**
  - Supabase 프로젝트 생성 및 URL, anon key 확보
  - `static/js/config.js`에서 설정 업데이트
- GitHub Pages 활성화
  - Settings → Pages → Source: "Deploy from a branch"
  - Branch: "main", Folder: "/ (root)"
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
- [x] 정적 사이트 구조: `index.html`, `practice.html`
- [x] 정적 폴더 `static/` 구성 (CSS, JavaScript 모듈)
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
- [x] Supabase JavaScript SDK를 통한 직접 데이터베이스 연결
- [x] 클라이언트 사이드 저장: `student_id`, `mode`, `wpm`, `accuracy`, `score`, `duration_sec`
- [x] **유효성 검증(클라이언트)**: 정규식 `^\d{5}\s[가-힣]{2,4}$`
- [x] **시간 검증**: `duration_sec >= 300` 인 경우만 저장
- [x] 프런트 입력창 placeholder: `"학번 이름 (예: 10218 홍길동)"`
- [x] **타임스탬프 개선**: 한국 시간(KST) 적용으로 실제 수업시간과 일치

## v0.6 대시보드 Top10 (완료)
- [x] JavaScript를 통한 Supabase 직접 쿼리
- [x] 정렬: score desc → accuracy desc → wpm desc → created_at asc
- [x] Top10 렌더링, 모드 탭 4개
- [x] **대시보드 통합**: 별도 페이지 제거하고 홈페이지에 순위표 통합

## v0.7 더 보기(페이지네이션) (완료)
- [x] JavaScript 클라이언트에서 limit/offset 처리
- [x] "더 보기" 클릭 시 10개씩 추가 로드
- [x] "전체 보기" 토글 또는 무한 스크롤 선택
- [x] **UI 개선**: "Top10 보기"/"전체 보기" 토글 버튼으로 전환 가능
- [x] **스크롤 개선**: 600px 높이 제한으로 깔끔한 인터페이스

## v0.7.1 데이터 품질 개선 (완료)
- [x] **WPM 재계산**: 기존 기록을 새로운 공식으로 일괄 업데이트
- [x] **타임스탬프 통합**: 기존 기록을 UTC에서 한국시간(+9시간)으로 변환
- [x] **관리자 기능**: 클라이언트 사이드 관리자 로그인 (localStorage 기반)
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

## v0.8 검색(부분 일치)
- [ ] 상단 검색 바(2자 이상 입력 시 동작, 디바운스 300ms)
- [ ] `search` 파라미터를 받아 `student_id ilike '%q%'`
- [ ] 검색+페이지네이션 동시 동작

## v0.9 교사 관리자 모드
- [ ] 우측 상단 "교사 로그인" 버튼 → 모달
- [ ] 인증(`ADMIN_USER`/`ADMIN_PASS`) 성공 시 토큰 발급(세션 스토리지)
- [ ] 관리자 전용 UI: 행 단위 **수정/삭제** 버튼
- [ ] `PATCH /api/records/{id}`, `DELETE /api/records/{id}` 구현(토큰 검사)

## v1.0 GitHub Pages 배포 (완료)
- [x] **Flask → 정적 사이트 전환**: Python 백엔드 제거, JavaScript 클라이언트 구현
- [x] **핵심 기능 완성**: 4개 모드, 실시간 성과 측정, 순위표, 데이터 저장
- [x] **데이터 품질**: WPM 공식 개선, 한국시간 타임스탬프, 기존 데이터 일괄 업데이트
- [x] **사용자 경험**: 홈페이지 순위표 통합, Top10/전체보기 토글, 반응형 디자인
- [x] **GitHub Pages 배포**: 정적 사이트 호스팅으로 서버 불필요
- [x] **Supabase 직접 연결**: JavaScript SDK를 통한 실시간 데이터베이스 연동
- [x] **복사/붙여넣기 방지**: 부정행위 방지 기능 구현

---

## 실행 가이드(GitHub Pages)
- `static/js/config.js`에서 Supabase URL과 키 설정
- GitHub 리포지토리에 코드 푸시
- Settings → Pages에서 배포 설정
- `https://username.github.io/repository-name` 접속
- 장치 보안: 관리자 자격은 config.js에 설정, 필요시 수정 가능

---

## 샘플 코드 스니펫

### JavaScript 클라이언트(요약)
```javascript
// config.js
const SUPABASE_CONFIG = {
    url: 'https://your-project-ref.supabase.co',
    key: 'your-anon-key-here'
};

// database.js
class DatabaseManager {
    async initialize() {
        this.supabase = supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.key);
    }
    
    async saveRecord(recordData) {
        const { data, error } = await this.supabase
            .from('records')
            .insert([recordData]);
        return { success: !error, data, error };
    }
    
    async getLeaderboard(mode, limit = 10) {
        const { data, error } = await this.supabase
            .from('records')
            .select('*')
            .eq('mode', mode)
            .order('score', { ascending: false })
            .limit(limit);
        return { records: data || [], error };
    }
}
