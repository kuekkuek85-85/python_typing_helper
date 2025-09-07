from app import app

# Replit에서 실행할 때 사용되는 엔트리 포인트
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
