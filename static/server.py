#!/usr/bin/env python3
"""
간단한 정적 파일 서버 (테스트용)
python static/server.py 실행 후 http://localhost:8000 접속
"""

import http.server
import socketserver
import os
import sys

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='.', **kwargs)

    def guess_type(self, path):
        mimetype = super().guess_type(path)
        # JavaScript 파일에 대한 올바른 MIME 타입 설정
        if path.endswith('.js'):
            return 'application/javascript'
        return mimetype

if __name__ == "__main__":
    # 현재 디렉토리를 프로젝트 루트로 변경
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    print(f"정적 파일 서버를 포트 {PORT}에서 시작합니다...")
    print(f"브라우저에서 http://localhost:{PORT} 에 접속하세요")
    print("서버를 중지하려면 Ctrl+C를 누르세요")
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버를 중지합니다...")
            httpd.shutdown()