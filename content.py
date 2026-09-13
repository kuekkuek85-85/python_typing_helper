"""연습 모드 정의와 연습용 텍스트 생성."""

import random

PRACTICE_MODES = {
    '자리': {
        'title': '자리 연습',
        'description': '파이썬 키워드와 기호를 연습하세요',
        'icon': '⌨️',
        'color': 'primary',
    },
    '낱말': {
        'title': '낱말 연습',
        'description': '파이썬 키워드와 함수명을 연습하세요',
        'icon': '📝',
        'color': 'success',
    },
    '문장': {
        'title': '문장 연습',
        'description': '파이썬 구문과 표현식을 연습하세요',
        'icon': '📋',
        'color': 'info',
    },
    '문단': {
        'title': '문단 연습',
        'description': '완전한 파이썬 코드 블록을 연습하세요',
        'icon': '📄',
        'color': 'warning',
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
