"""Vercel 서버리스 함수 엔트리 포인트.

Vercel의 Python 런타임은 `api/` 아래 모듈에서 `app`이라는 이름의 WSGI
애플리케이션을 찾는다. `vercel.json`이 모든 경로를 이 함수로 넘기므로
정적 파일도 Flask가 서빙한다.

⚠️ 서버리스에서는 요청마다 프로세스가 달라질 수 있다. 연습 세션을 프로세스
메모리에 두면 학생이 기록을 저장할 수 없으므로, 반드시 환경 변수
`SESSION_BACKEND=firestore`로 두어야 한다(Vercel에서는 auto도 이렇게 고른다 —
config.SERVERLESS 참고). 배포 후 `/health`의 `session_backend` 값으로 확인한다.

일반 서버(gunicorn) 배포는 이 파일이 아니라 `main.py`를 쓴다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402

# Vercel 런타임이 이 이름을 찾는다. 재노출이므로 린터에 알려 둔다.
__all__ = ['app']
