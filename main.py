import os
from app import app

# 배포 플랫폼에서 실행할 때 사용되는 엔트리 포인트
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
