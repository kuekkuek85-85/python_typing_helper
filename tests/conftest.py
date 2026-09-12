"""테스트 공통 설정."""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('SESSION_SECRET', 'test-secret')
os.environ.setdefault('STORE_BACKEND', 'local')
os.environ.setdefault('LOG_LEVEL', 'WARNING')

from app import create_app  # noqa: E402
from store import LocalJsonStore  # noqa: E402


@pytest.fixture
def record_store(tmp_path):
    return LocalJsonStore(path=str(tmp_path / 'records.json'))


@pytest.fixture
def app(record_store):
    flask_app = create_app(record_store=record_store)
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def practice_flow(app, client):
    """연습 세션을 만들고 서버 검증을 통과할 상태로 만들어 주는 도우미."""

    class PracticeFlow:
        def __init__(self):
            self.token = None
            self.session_id = None

        def open(self, mode='자리'):
            response = client.get(f'/practice/{mode}')
            assert response.status_code == 200
            with client.session_transaction() as session:
                self.token = session['practice']['token']
                self.session_id = session['practice']['session_id']
            return self

        def start(self):
            response = client.post('/api/practice/start', json={'practice_token': self.token})
            assert response.status_code == 200, response.get_json()
            return self

        def activity(self):
            return app.extensions['typing_sessions'].get(self.session_id)

        def simulate(self, keystrokes=600, elapsed=305.0, span=290.0):
            """실제로 연습한 것과 같은 상태를 만든다(시간을 과거로 조정)."""
            activity = self.activity()
            now = time.time()
            activity.started_at = now - elapsed
            activity.count = keystrokes
            activity.first_keystroke_at = now - span
            activity.last_keystroke_at = now
            return self

        def save(self, **overrides):
            payload = {
                'student_id': '10218 홍길동',
                'wpm': 200,
                'accuracy': 95.0,
                'practice_token': self.token,
            }
            payload.update(overrides)
            return client.post('/api/records', json=payload)

    return PracticeFlow()
