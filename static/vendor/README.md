# 포함된 외부 라이브러리 (vendored)

학교 네트워크에서 CDN 접속이 막히면 모달·탭이 동작하지 않아 학생이 기록을
저장할 수 없다. 그래서 아래 파일들을 프로젝트에 함께 넣었다.

| 파일 | 라이브러리 | 버전 | 라이선스 |
| --- | --- | --- | --- |
| `bootstrap/bootstrap.min.css` | Bootstrap | 5.3.8 | MIT |
| `bootstrap/bootstrap.min.js` | Bootstrap | 5.3.8 | MIT |
| `bootstrap/popper.min.js` | Popper | Bootstrap 배포본 동봉 | MIT |
| `bootstrap-icons/` | Bootstrap Icons | 1.13.1 | MIT |

## 업데이트 방법

https://getbootstrap.com/docs/5.3/getting-started/download/ 에서 컴파일된
CSS/JS를 받아 같은 경로의 파일을 덮어쓴다. Bootstrap Icons는
https://icons.getbootstrap.com 에서 받고, `bootstrap-icons.min.css`가
`fonts/` 아래의 woff/woff2를 상대 경로로 참조하므로 폴더 구조를 유지한다.

업데이트 후에는 홈 화면의 탭/모달과 연습 화면의 완료 모달이 뜨는지 확인한다.
