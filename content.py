"""연습 모드 정의와 연습용 텍스트 생성."""

import random

# 홈 화면에서 어떤 모드를 열어 둘지는 **여기 `available` 한 곳**에서 정한다.
# 예전에는 템플릿의 `{% if mode_key == '자리' %}` 조건에 흩어져 있었다.
#
# `available: False`인 모드는 홈 화면에서 '추후 제공' 안내만 뜬다. API와 연습
# 로직은 그대로 동작하므로, 주소를 직접 아는 사람은 들어갈 수 있다. 수업 중
# 학생이 다른 모드로 새는 것을 막는 용도이지 접근 차단이 아니다.
PRACTICE_MODES = {
    '자리': {
        'title': '자리 연습',
        'description': '파이썬 키워드와 기호를 연습하세요',
        'icon': '⌨️',
        'color': 'primary',
        'available': True,
    },
    '낱말': {
        'title': '낱말 연습',
        'description': '파이썬 키워드와 함수명을 연습하세요',
        'icon': '📝',
        'color': 'success',
        'available': False,
        # 다시 열 때 이 배지가 함께 돌아온다.
        'badge': 'BETA',
    },
    '문장': {
        'title': '문장 연습',
        'description': '파이썬 구문과 표현식을 연습하세요',
        'icon': '📋',
        'color': 'info',
        'available': False,
    },
    '문단': {
        'title': '문단 연습',
        'description': '완전한 파이썬 코드 블록을 연습하세요',
        'icon': '📄',
        'color': 'warning',
        'available': False,
    },
}

# '자리' 연습은 아래 풀에서 무작위로 뽑아 매번 새로운 줄을 만든다.
KEYBOARD_CHARS = ['asdf', 'jkl;', 'qwer', 'uiop', 'zxcv', 'bnm,']
PYTHON_KEYWORDS = ['if', 'else', 'def', 'for', 'while', 'and', 'or', 'not', 'in', 'is',
                   'True', 'False', 'None']
PYTHON_FUNCTIONS = ['print()', 'input()', 'len()', 'str()', 'int()', 'float()', 'bool()',
                    'list()', 'dict()']
SYMBOLS = ['[]', '{}', '()', '""', "''", ':', ';', ',', '.', '/', '?', '!', '@', '#', '$',
           '%', '^', '&', '*', '-', '+', '=', '_']

CHARACTER_POOL = KEYBOARD_CHARS + PYTHON_KEYWORDS + PYTHON_FUNCTIONS + SYMBOLS

PRACTICE_TEXTS = {
    '낱말': [
        'print input len str int float bool list dict tuple',
        'def if else elif for while and or not in is',
        'True False None return break continue pass',
        'append remove pop sort index count reverse',
        'range type isinstance hasattr getattr setattr',
    ],
    '문장': [
        'print("Hello, World!")',
        'for i in range(10):',
        'if x > 0 and x < 100:',
        'name = input("Enter your name: ")',
        'numbers = [1, 2, 3, 4, 5]',
    ],
    '문단': [
        'def factorial(n):\n'
        '    if n <= 1:\n'
        '        return 1\n'
        '    else:\n'
        '        return n * factorial(n - 1)',

        'numbers = [1, 2, 3, 4, 5]\n'
        'for num in numbers:\n'
        '    if num % 2 == 0:\n'
        '        print(f"{num} is even")',

        'class Student:\n'
        '    def __init__(self, name, age):\n'
        '        self.name = name\n'
        '        self.age = age',
    ],
}


def build_practice_text(mode: str, exclude: str | None = None) -> str:
    """모드에 맞는 연습 텍스트를 하나 돌려준다.

    exclude: 직전에 사용한 텍스트. 가능하면 연속으로 같은 텍스트를 주지 않는다.
    """
    if mode == '자리':
        items = random.sample(CHARACTER_POOL, random.randint(15, 20))
        return ' '.join(items)

    texts = PRACTICE_TEXTS.get(mode, [])
    if not texts:
        raise KeyError(mode)

    candidates = [text for text in texts if text != exclude] or texts
    return random.choice(candidates)
