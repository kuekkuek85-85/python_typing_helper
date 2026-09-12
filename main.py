"""WSGI 엔트리 포인트 (gunicorn main:app)."""

import os

from app import app

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug)
