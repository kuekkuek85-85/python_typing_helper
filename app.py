"""파이썬 타자 도우미 - Flask 애플리케이션.

데이터는 Firebase Firestore(Admin SDK)에 저장한다. 자격 증명이 없으면
로컬 JSON 파일로 자동 전환되므로 Firebase 설정 없이도 앱이 뜬다(store.py 참고).
"""

from __future__ import annotations

import logging
import os
import secrets

from flask import Flask, jsonify, render_template, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

import config
import content
import scoring
import store as store_module
from sessions import RateLimiter, TypingSessionRegistry

logger = logging.getLogger(__name__)

# 한 번의 요청으로 보고할 수 있는 최대 키 입력 수(클라이언트는 약 2초마다 묶어 보낸다).
MAX_KEYSTROKES_PER_REQUEST = 200


def _configure_logging() -> None:
    level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(level=getattr(logging, level_name, logging.INFO),
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')


def _resolve_secret_key() -> str:
    secret = os.environ.get('SESSION_SECRET')
    if secret:
        return secret
    logger.warning(
        'SESSION_SECRET이 설정되지 않아 임시 키를 생성했습니다. '
        '서버를 다시 시작하면 진행 중인 연습 세션이 모두 끊깁니다. '
        '배포 시에는 반드시 SESSION_SECRET을 설정하세요.'
    )
    return secrets.token_urlsafe(32)


def create_app(record_store: store_module.RecordStore | None = None) -> Flask:
    _configure_logging()

    app = Flask(__name__)
    app.secret_key = _resolve_secret_key()
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_for=1)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
        # 이 앱의 요청 본문은 모두 작은 JSON이다. 과도한 본문은 미리 차단한다.
        MAX_CONTENT_LENGTH=32 * 1024,
    )
    app.json.ensure_ascii = False

    app.extensions['record_store'] = record_store or store_module.create_store()
    app.extensions['typing_sessions'] = TypingSessionRegistry()
    app.extensions['rate_limiter'] = RateLimiter()

    _register_routes(app)
    logger.info('저장소 백엔드: %s', app.extensions['record_store'].backend)
    return app


# --- 헬퍼 ----------------------------------------------------------------
def _store() -> store_module.RecordStore:
    from flask import current_app
    return current_app.extensions['record_store']


def _typing_sessions() -> TypingSessionRegistry:
    from flask import current_app
    return current_app.extensions['typing_sessions']


def _rate_limiter() -> RateLimiter:
    from flask import current_app
    return current_app.extensions['rate_limiter']


def _practice_session() -> dict | None:
    """세션에 저장된 연습 정보. 없으면 None."""
    practice = session.get('practice')
    if isinstance(practice, dict) and practice.get('token') and practice.get('session_id'):
        return practice
    return None


def _clear_practice_session() -> None:
    practice = session.pop('practice', None)
    session.pop('last_practice_text', None)
    if practice:
        _typing_sessions().discard(practice.get('session_id'))


def _authorized_practice(payload: dict) -> tuple[dict | None, tuple | None]:
    """연습 세션과 토큰을 검증한다. 실패하면 (None, 응답)을 돌려준다."""
    practice = _practice_session()
    if practice is None:
        return None, (jsonify({'error': '유효하지 않은 연습 세션입니다. 다시 연습을 시작해주세요.'}), 401)

    provided_token = payload.get('practice_token')
    if not provided_token or not secrets.compare_digest(str(provided_token), practice['token']):
        return None, (jsonify({'error': '인증 토큰이 일치하지 않습니다.'}), 401)

    return practice, None


def _json_body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


# --- 라우트 --------------------------------------------------------------
def _register_routes(app: Flask) -> None:

    @app.route('/')
    def index():
        """홈페이지 - 연습 모드 선택과 명예의 전당(순위표는 JS가 API로 채운다)."""
        return render_template('index.html', modes=content.PRACTICE_MODES)

    @app.route('/practice/<mode>')
    def practice(mode):
        """연습 화면. 연습마다 1회용 토큰을 발급한다."""
        if mode not in content.PRACTICE_MODES:
            return render_template('index.html', modes=content.PRACTICE_MODES), 404

        # 이전 연습이 남아 있으면 정리한다.
        _clear_practice_session()

        practice_token = secrets.token_urlsafe(32)
        session_id = secrets.token_urlsafe(16)
        session['practice'] = {
            'token': practice_token,
            'session_id': session_id,
            'mode': mode,
        }
        _typing_sessions().create(session_id)

        return render_template(
            'practice.html',
            mode=mode,
            mode_info=content.PRACTICE_MODES[mode],
            practice_token=practice_token,
            practice_seconds=config.PRACTICE_SECONDS,
        )

    @app.route('/health')
    def health():
        """헬스체크 - 저장소 연결 상태 포함."""
        record_store = _store()
        connected = record_store.ping()
        return jsonify({
            'status': 'healthy' if connected else 'unhealthy',
            'backend': record_store.backend,
            'database_connected': connected,
        }), (200 if connected else 503)

    @app.route('/api/practice/start', methods=['POST'])
    def start_practice():
        """'연습 시작' 버튼을 눌렀을 때 서버 측 타이머를 시작한다."""
        practice, error = _authorized_practice(_json_body())
        if error:
            return error

        activity = _typing_sessions().start(practice['session_id'])
        if activity is None:
            return jsonify({'error': '연습 세션이 만료되었습니다. 페이지를 새로고침해주세요.'}), 409

        return jsonify({'success': True, 'practice_seconds': config.PRACTICE_SECONDS})

    @app.route('/api/keystroke', methods=['POST'])
    def record_keystroke():
        """타이핑 활동 기록. 클라이언트가 키 입력 수를 묶어서 보고한다."""
        payload = _json_body()
        practice, error = _authorized_practice(payload)
        if error:
            return error

        try:
            count = int(payload.get('count', 1))
        except (TypeError, ValueError):
            return jsonify({'error': 'count 값이 올바르지 않습니다.'}), 400

        count = max(1, min(count, MAX_KEYSTROKES_PER_REQUEST))

        activity = _typing_sessions().add_keystrokes(practice['session_id'], count)
        if activity is None:
            return jsonify({'error': '연습이 시작되지 않았습니다.'}), 409

        return jsonify({'success': True, 'count': activity.count})

    @app.route('/api/records', methods=['POST'])
    def create_record():
        """연습 기록 저장.

        연습 시간과 점수는 **서버가 계산**한다. 클라이언트가 보낸 duration_sec,
        score 값은 사용하지 않는다.
        """
        payload = _json_body()
        if not payload:
            return jsonify({'error': '잘못된 요청 데이터입니다.'}), 400

        practice, error = _authorized_practice(payload)
        if error:
            return error

        mode = practice['mode']
        if mode not in content.PRACTICE_MODES:
            return jsonify({'error': '올바르지 않은 연습 모드입니다.'}), 400

        student_id = str(payload.get('student_id', '')).strip()
        is_valid, message = scoring.validate_student_id(student_id)
        if not is_valid:
            return jsonify({'error': message}), 400

        try:
            wpm = int(payload['wpm'])
            accuracy = float(payload['accuracy'])
        except (KeyError, TypeError, ValueError):
            return jsonify({'error': '분당 타수와 정확도를 숫자로 보내주세요.'}), 400

        # 1) 실제로 연습을 진행했는지 확인한다.
        activity = _typing_sessions().get(practice['session_id'])
        if activity is None or activity.started_at is None:
            return jsonify({'error': '연습 기록을 찾을 수 없습니다. 다시 연습을 시작해주세요.'}), 409

        elapsed = activity.elapsed_seconds
        if elapsed < config.PRACTICE_SECONDS:
            return jsonify({'error': f'{config.PRACTICE_SECONDS // 60}분 종료 후 저장 가능합니다.'}), 400

        if elapsed > config.PRACTICE_SECONDS + config.SAVE_GRACE_SECONDS:
            return jsonify({'error': '연습 완료 후 너무 많은 시간이 경과했습니다. 다시 연습해주세요.'}), 400

        # 저장되는 연습 시간은 항상 규정 연습 시간이다(클라이언트 값 신뢰하지 않음).
        duration_sec = config.PRACTICE_SECONDS

        is_valid, message = scoring.validate_typing_activity(activity, duration_sec)
        if not is_valid:
            return jsonify({'error': message}), 400

        # 2) 성능 수치가 현실적인지 확인한다.
        is_valid, message = scoring.validate_metrics(wpm, accuracy)
        if not is_valid:
            return jsonify({'error': message}), 400

        is_valid, message = scoring.validate_wpm_against_keystrokes(
            wpm, activity.count, duration_sec)
        if not is_valid:
            return jsonify({'error': message}), 400

        # 3) 제출 빈도 제한(검증을 모두 통과한 요청에만 적용).
        if not _rate_limiter().allow(student_id):
            return jsonify({
                'error': f'너무 빠른 제출입니다. {config.RATE_LIMIT_WINDOW // 60}분당 최대 '
                         f'{config.MAX_SUBMISSIONS_PER_WINDOW}번만 제출 가능합니다.'
            }), 429

        score = scoring.compute_score(wpm, accuracy)

        try:
            saved = _store().add(student_id=student_id, mode=mode, wpm=wpm, accuracy=accuracy,
                                 score=score, duration_sec=duration_sec)
        except Exception as error:  # noqa: BLE001 - 저장 실패는 사용자에게 일반 메시지로 알린다
            logger.exception('기록 저장 실패: %s', error)
            return jsonify({'error': '기록을 저장하지 못했습니다. 잠시 후 다시 시도해주세요.'}), 503

        # 토큰은 1회용이다. 저장 후 세션과 타이핑 기록을 모두 폐기한다.
        _clear_practice_session()

        logger.info('기록 저장 성공: %s, %s, %s점, IP: %s',
                    student_id, mode, score, request.remote_addr)

        return jsonify({
            'success': True,
            'message': '기록이 성공적으로 저장되었습니다.',
            'id': saved['id'],
            'score': score,
            'wpm': wpm,
            'accuracy': accuracy,
        }), 201

    @app.route('/api/records/top')
    def get_top_records():
        """모드별 상위 10개 기록."""
        mode = request.args.get('mode', '자리')
        if mode not in content.PRACTICE_MODES:
            return jsonify({'error': '올바르지 않은 연습 모드입니다.'}), 400

        try:
            records = _store().top(mode, 10)
        except Exception as error:  # noqa: BLE001
            logger.exception('랭킹 조회 실패: %s', error)
            return jsonify({'error': '기록을 불러오지 못했습니다.'}), 503

        return jsonify({
            'success': True,
            'mode': mode,
            'records': [store_module.to_api_dict(record) for record in records],
            'total': len(records),
        })

    @app.route('/api/records')
    def get_records():
        """페이지네이션된 기록 조회."""
        mode = request.args.get('mode', '자리')
        if mode not in content.PRACTICE_MODES:
            return jsonify({'error': '올바르지 않은 연습 모드입니다.'}), 400

        try:
            limit = int(request.args.get('limit', 10))
            offset = int(request.args.get('offset', 0))
        except ValueError:
            return jsonify({'error': 'limit 또는 offset이 올바르지 않습니다.'}), 400

        limit = max(1, min(limit, config.MAX_PAGE_SIZE))
        offset = max(0, offset)

        try:
            records, total = _store().page(mode, limit, offset)
        except Exception as error:  # noqa: BLE001
            logger.exception('기록 조회 실패: %s', error)
            return jsonify({'error': '기록을 불러오지 못했습니다.'}), 503

        return jsonify({
            'success': True,
            'mode': mode,
            'records': [store_module.to_api_dict(record) for record in records],
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total,
                'has_more': offset + limit < total,
                'current_count': len(records),
            },
        })

    # 참고: 전체 통계 API(`GET /api/records/stats`)는 v0.8에서 제거했다.
    # 호출하는 화면이 없는데 평균·고유 학생 수를 구하느라 모든 기록을 읽었다.
    # 교사 대시보드(SRD v0.9)에서 이 수치가 실제로 필요해지면, 그때 반·기간 축으로
    # 설계하고 저장 시 요약 문서를 갱신하는 방식으로 다시 만든다.

    @app.route('/api/practice-text/<mode>')
    def get_practice_text(mode):
        """연습용 텍스트. 가능하면 직전 텍스트와 다른 것을 돌려준다."""
        if mode not in content.PRACTICE_MODES:
            return jsonify({'error': '올바르지 않은 연습 모드입니다.'}), 400

        try:
            text = content.build_practice_text(mode, exclude=session.get('last_practice_text'))
        except KeyError:
            return jsonify({'error': '연습 텍스트를 찾을 수 없습니다.'}), 404

        session['last_practice_text'] = text

        response = jsonify({'success': True, 'mode': mode, 'text': text})
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': '요청한 API를 찾을 수 없습니다.'}), 404
        return render_template('index.html', modes=content.PRACTICE_MODES), 404

    @app.errorhandler(500)
    def handle_server_error(error):
        logger.exception('처리되지 않은 서버 오류: %s', error)
        if request.path.startswith('/api/'):
            return jsonify({'error': '서버 오류가 발생했습니다.'}), 500
        return render_template('index.html', modes=content.PRACTICE_MODES), 500


app = create_app()


if __name__ == '__main__':
    # 로컬 개발용. 배포는 gunicorn을 사용한다(Procfile 참고).
    debug = os.environ.get('FLASK_DEBUG', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug)
