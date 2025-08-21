import os
import logging
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# 디버그 로깅 설정
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# 데이터베이스 초기화
db = SQLAlchemy(model_class=Base)

# Flask 앱 초기화
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-for-development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# 데이터베이스 설정
database_url = os.environ.get("DATABASE_URL")

# DB URL 처리 및 연결 최적화
if database_url:
    # postgres://를 postgresql://로 변경
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    elif database_url.startswith("https://"):
        logging.warning("DATABASE_URL이 HTTPS 형식입니다. PostgreSQL 연결 문자열이 필요합니다.")
        logging.warning("Supabase에서 올바른 Database URL을 복사해주세요.")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 10,
    "pool_size": 5,
    "max_overflow": 0,
    "connect_args": {
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"
    }
}

# 데이터베이스 초기화
db.init_app(app)

# 관리자 계정 설정
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin")

# 학생 ID 검증용 정규식
ID_PATTERN = re.compile(r"^\d{5}\s[가-힣]{2,4}$")

# 데이터베이스 모델
class Record(db.Model):
    __tablename__ = 'records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    mode = db.Column(db.String(10), nullable=False)
    wpm = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    duration_sec = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'mode': self.mode,
            'wpm': self.wpm,
            'accuracy': self.accuracy,
            'score': self.score,
            'duration_sec': self.duration_sec,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# 연습 모드별 데이터
PRACTICE_MODES = {
    '자리': {
        'title': '자리 연습',
        'description': '파이썬 키워드와 키보드를 연습하세요',
        'icon': '⌨️',
        'color': 'primary'
    },
    '낱말': {
        'title': '낱말 연습',
        'description': '파이썬 키워드와 함수명을 연습하세요',
        'icon': '📝',
        'color': 'success'
    },
    '문장': {
        'title': '문장 연습',
        'description': '파이썬 구문과 표현식을 연습하세요',
        'icon': '📋',
        'color': 'info'
    },
    '문단': {
        'title': '문단 연습',
        'description': '완전한 파이썬 코드 블록을 연습하세요',
        'icon': '📄',
        'color': 'warning'
    }
}

@app.route('/')
def index():
    """홈페이지 - 연습 모드 선택"""
    try:
        # 자리 연습 모드의 상위 10개 기록 조회
        top_records = Record.query.filter_by(mode='자리')\
            .order_by(Record.score.desc(), Record.accuracy.desc(), Record.wpm.desc(), Record.created_at.asc())\
            .limit(10)\
            .all()
        
        return render_template('index.html', modes=PRACTICE_MODES, top_records=top_records)
    except Exception as e:
        logging.error(f"홈페이지 로딩 실패: {e}")
        # 에러 발생 시에도 페이지는 표시되도록
        return render_template('index.html', modes=PRACTICE_MODES, top_records=[])

@app.route('/practice/<mode>')
def practice(mode):
    """연습 화면"""
    if mode not in PRACTICE_MODES:
        return "잘못된 연습 모드입니다.", 404
    
    mode_info = PRACTICE_MODES[mode]
    return render_template('practice.html', mode=mode, mode_info=mode_info)

@app.route('/dashboard')
def dashboard():
    """대시보드 페이지 - Top10 랭킹"""
    return render_template('dashboard.html', modes=PRACTICE_MODES)

@app.route('/health')
def health():
    """헬스체크 엔드포인트"""
    try:
        # 데이터베이스 연결 테스트
        db.session.execute(db.text('SELECT 1'))
        db_status = True
    except Exception as e:
        db_status = False
        logging.error(f"데이터베이스 연결 실패: {e}")
    
    status = {
        'status': 'healthy' if db_status else 'unhealthy',
        'database_connected': db_status
    }
    return jsonify(status)

# API 엔드포인트 - 기록 저장
@app.route('/api/records', methods=['POST'])
def create_record():
    """연습 기록 저장"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '잘못된 요청 데이터입니다.'}), 400
        
        # 필수 필드 검증
        required_fields = ['student_id', 'mode', 'wpm', 'accuracy', 'score', 'duration_sec']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} 필드가 필요합니다.'}), 400
        
        student_id = data['student_id'].strip()
        mode = data['mode']
        wpm = int(data['wpm'])
        accuracy = float(data['accuracy'])
        score = int(data['score'])
        duration_sec = int(data['duration_sec'])
        
        # 학생 ID 형식 검증
        if not ID_PATTERN.match(student_id):
            return jsonify({'error': '학번 이름 형식이 올바르지 않습니다. (예: 10218 홍길동)'}), 400
        
        # 연습 시간 검증 (5분 = 300초)
        if duration_sec < 300:
            return jsonify({'error': '5분 종료 후 저장 가능합니다.'}), 400
        
        # 모드 검증
        if mode not in PRACTICE_MODES:
            return jsonify({'error': '올바르지 않은 연습 모드입니다.'}), 400
        
        # 새 기록 생성
        new_record = Record()
        new_record.student_id = student_id
        new_record.mode = mode
        new_record.wpm = wpm
        new_record.accuracy = accuracy
        new_record.score = score
        new_record.duration_sec = duration_sec
        
        db.session.add(new_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '기록이 성공적으로 저장되었습니다.',
            'id': new_record.id
        }), 201
        
    except ValueError as e:
        return jsonify({'error': '숫자 형식이 올바르지 않습니다.'}), 400
    except Exception as e:
        logging.error(f"기록 저장 실패: {e}")
        db.session.rollback()
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

# API 엔드포인트 - 랭킹 조회
@app.route('/api/records/top')
def get_top_records():
    """상위 10개 기록 조회"""
    try:
        mode = request.args.get('mode', '자리')
        if mode not in PRACTICE_MODES:
            return jsonify({'error': '올바르지 않은 연습 모드입니다.'}), 400
        
        # 상위 10개 기록 조회 (점수 desc, 정확도 desc, WPM desc, 날짜 asc 순)
        records = Record.query.filter_by(mode=mode)\
            .order_by(Record.score.desc(), Record.accuracy.desc(), Record.wpm.desc(), Record.created_at.asc())\
            .limit(10)\
            .all()
        
        return jsonify({
            'success': True,
            'mode': mode,
            'records': [record.to_dict() for record in records],
            'total': len(records)
        })
        
    except Exception as e:
        logging.error(f"랭킹 조회 실패: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

# API 엔드포인트 - 통계 조회
@app.route('/api/records/stats')
def get_statistics():
    """전체 통계 조회"""
    try:
        # 전체 학생 수 (고유 student_id)
        total_students = db.session.query(Record.student_id).distinct().count()
        
        # 전체 기록 수
        total_records = Record.query.count()
        
        # 평균 WPM (모든 기록의 평균)
        avg_wpm_result = db.session.query(db.func.avg(Record.wpm)).scalar()
        avg_wpm = float(avg_wpm_result) if avg_wpm_result else 0
        
        # 평균 정확도 (모든 기록의 평균)
        avg_accuracy_result = db.session.query(db.func.avg(Record.accuracy)).scalar()
        avg_accuracy = float(avg_accuracy_result) if avg_accuracy_result else 0
        
        return jsonify({
            'success': True,
            'total_students': total_students,
            'total_records': total_records,
            'avg_wpm': avg_wpm,
            'avg_accuracy': avg_accuracy
        })
        
    except Exception as e:
        logging.error(f"통계 조회 실패: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

# API 엔드포인트 - 페이지네이션된 기록 조회
@app.route('/api/records')
def get_records():
    """페이지네이션된 기록 조회"""
    try:
        mode = request.args.get('mode', '자리')
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        if mode not in PRACTICE_MODES:
            return jsonify({'error': '올바르지 않은 연습 모드입니다.'}), 400
        
        # limit 범위 제한 (1-50)
        limit = max(1, min(limit, 50))
        # offset 음수 방지
        offset = max(0, offset)
        
        # 총 기록 수 조회
        total_count = Record.query.filter_by(mode=mode).count()
        
        # 페이지네이션된 기록 조회
        records = Record.query.filter_by(mode=mode)\
            .order_by(Record.score.desc(), Record.accuracy.desc(), Record.wpm.desc(), Record.created_at.asc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        # 다음 페이지 존재 여부
        has_more = (offset + limit) < total_count
        
        return jsonify({
            'success': True,
            'mode': mode,
            'records': [record.to_dict() for record in records],
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total_count,
                'has_more': has_more,
                'current_count': len(records)
            }
        })
        
    except ValueError:
        return jsonify({'error': 'limit 또는 offset이 올바르지 않습니다.'}), 400
    except Exception as e:
        logging.error(f"기록 조회 실패: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

# API 엔드포인트 - 연습 텍스트 가져오기
@app.route('/api/practice-text/<mode>')
def get_practice_text(mode):
    """연습용 텍스트 가져오기"""
    if mode not in PRACTICE_MODES:
        return jsonify({'error': '올바르지 않은 연습 모드입니다.'}), 400
    
    # 정적 데이터에서 랜덤하게 선택
    import random
    
    # 자리 연습용 키워드 풀
    keyboard_chars = ['asdf', 'jkl;', 'qwer', 'uiop', 'zxcv', 'bnm,']
    python_keywords = ['if', 'else', 'def', 'for', 'while', 'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None']
    python_functions = ['print()', 'input()', 'len()', 'str()', 'int()', 'float()', 'bool()', 'list()', 'dict()']
    symbols = ['[]', '{}', '()', '""', "''", ':', ';', ',', '.', '/', '?', '!', '@', '#', '$', '%', '^', '&', '*', '-', '+', '=', '_']
    
    practice_texts = {
        '자리': [],  # 동적으로 생성됨
        '낱말': [
            'print input len str int float bool list dict tuple',
            'def if else elif for while and or not in is',
            'True False None return break continue pass',
            'append remove pop sort index count reverse',
            'range type isinstance hasattr getattr setattr'
        ],
        '문장': [
            'print("Hello, World!")',
            'for i in range(10):',
            'if x > 0 and x < 100:',
            'name = input("Enter your name: ")',
            'numbers = [1, 2, 3, 4, 5]'
        ],
        '문단': [
            '''def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)''',
            '''numbers = [1, 2, 3, 4, 5]
for num in numbers:
    if num % 2 == 0:
        print(f"{num} is even")''',
            '''class Student:
    def __init__(self, name, age):
        self.name = name
        self.age = age'''
        ]
    }
    
    if mode == '자리':
        # 자리 연습의 경우 랜덤하게 섞인 텍스트 생성
        all_items = keyboard_chars + python_keywords + python_functions + symbols
        random.shuffle(all_items)
        
        # 15-20개 항목을 선택해서 하나의 연습 텍스트로 만들기
        num_items = random.randint(15, 20)
        selected_items = all_items[:num_items]
        selected_text = ' '.join(selected_items)
    else:
        texts = practice_texts.get(mode, [])
        if not texts:
            return jsonify({'error': '연습 텍스트를 찾을 수 없습니다.'}), 404
        
        selected_text = random.choice(texts)
    
    return jsonify({
        'success': True,
        'mode': mode,
        'text': selected_text
    })

# 데이터베이스 테이블 생성
with app.app_context():
    try:
        db.create_all()
        logging.info("데이터베이스 테이블이 성공적으로 생성되었습니다.")
        
        # 테스트 데이터 추가 (개발용)
        if Record.query.count() == 0:
            test_records = [
                {'student_id': '10130 홍길동', 'mode': '자리', 'wpm': 45, 'accuracy': 92.5, 'score': 370, 'duration_sec': 300},
                {'student_id': '10215 김영희', 'mode': '자리', 'wpm': 38, 'accuracy': 96.0, 'score': 350, 'duration_sec': 300},
                {'student_id': '10302 박철수', 'mode': '자리', 'wpm': 52, 'accuracy': 89.2, 'score': 415, 'duration_sec': 300}
            ]
            for record_data in test_records:
                record = Record(**record_data)
                db.session.add(record)
            db.session.commit()
            logging.info("테스트 데이터가 추가되었습니다.")
            
    except Exception as e:
        logging.error(f"데이터베이스 테이블 생성 실패: {e}")
        logging.info("Replit PostgreSQL 데이터베이스를 사용합니다.")

if __name__ == '__main__':
    # 개발 환경에서 디버그 모드로 실행
    app.run(host='0.0.0.0', port=5000, debug=True)
