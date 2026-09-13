# 연습 세션 정보가 프로세스 메모리에 있으므로 워커는 반드시 1개여야 한다.
# 동시 접속은 스레드로 처리한다. (sessions.py 주석 참고)
web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 60 main:app
