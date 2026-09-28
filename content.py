"""연습 모드 정의와 연습용 텍스트 생성.

자리 연습은 **예제 목록**(EXAMPLE_SETS) 중 하나를 골라 그 줄들을 무작위로
보여준다. 어떤 목록을 쓸지는 교사 대시보드에서 바꿀 수 있고, 그 선택은
DB에 저장된다(catalog.py). 여기 정의된 것은 코드에 내장된 기본 목록이다.
"""

import random
import re

# 홈 화면에서 어떤 모드를 열어 둘지의 **기본값**. 실제로 열려 있는지는 교사
# 대시보드에서 바꿀 수 있고 DB에 저장된다(catalog.effective_modes가 합친다).
#
# `available: False`인 모드는 홈 화면에서 '추후 제공' 안내만 뜬다. API와 연습
# 로직은 그대로 동작하므로, 주소를 직접 아는 사람은 들어갈 수 있다. 수업 중
# 학생이 다른 모드로 새는 것을 막는 용도이지 접근 차단이 아니다.
PRACTICE_MODES = {
    '자리': {
        'title': '자리 연습',
        'description': '터틀 예제 코드를 한 줄씩 연습하세요',
        'icon': '⌨️',
        'color': 'primary',
        'available': True,
    },
    '낱말': {
        'title': '낱말 연습',
        'description': '터틀 예제의 낱말(키워드·함수명)을 연습하세요',
        'icon': '📝',
        'color': 'success',
        'available': True,
    },
    '문장': {
        'title': '문장 연습',
        'description': '터틀 예제의 코드 한 줄을 연습하세요',
        'icon': '📋',
        'color': 'info',
        'available': True,
    },
    '문단': {
        'title': '문단 연습',
        'description': '터틀 예제의 완성 코드 블록을 연습하세요',
        'icon': '📄',
        'color': 'warning',
        'available': True,
    },
}


# --- 자리 연습 예제 목록 --------------------------------------------------
# 「터틀 타이핑 예제」의 원본 마크다운. 교사가 올린 정답 코드 그대로이며,
# DB 백업의 원본으로도 쓴다(catalog.backup_document). 여기가 원본(source of
# truth)이고, DB에는 이것과 아래에서 만든 줄 목록을 함께 백업한다.
TURTLE_SOURCE_MARKDOWN = '''# 파이썬 타자 도우미 — 터틀 예제 코드 (정답)

정보 15·16차 「빈칸 채우기」의 완성(정답) 코드입니다. 값은 포털 예제 기본값(주인공 square·green, `goto(0, -250)` 등 완성 게임 기준)으로 채웠습니다.

- 15차: 주제1(무대) · 주제2(거북이)
- 16차: 주제2~5 중 반별 시작 주제부터 (1반=거북이, 3·2·4반=펜)

---

## 주제1 — 무대 (screen)

```python
import turtle

screen = turtle.Screen()
screen.title("My Game")
screen.bgcolor("lightyellow")
screen.setup(600, 600)

screen.mainloop()
```

## 주제2 — 거북이 (shape · color)

```python
import turtle

screen = turtle.Screen()
screen.setup(600, 600)

player = turtle.Turtle()
player.shape("square")
player.color("green")

screen.mainloop()
```

## 주제3 — 펜 (penup · pendown)

```python
import turtle
import time

screen = turtle.Screen()
screen.setup(600, 600)

player = turtle.Turtle()
player.forward(100)
time.sleep(1)
player.penup()
player.forward(100)
time.sleep(1)
player.pendown()
player.forward(100)

screen.mainloop()
```

## 주제4 — 좌표 (goto · setx)

```python
import turtle
import time

screen = turtle.Screen()
screen.setup(600, 600)

player = turtle.Turtle()
player.penup()
player.goto(0, -250)
time.sleep(1)
player.setx(100)
time.sleep(1)
player.setx(-100)

screen.mainloop()
```

## 주제5 — 이동 (forward · left · right)

```python
import turtle
import time

screen = turtle.Screen()
screen.setup(600, 600)

player = turtle.Turtle()
player.forward(100)
time.sleep(0.5)
player.left(90)
player.forward(100)

screen.mainloop()
```

---

## 참고: 빈칸(★★★) 자리 (타자 도우미에서 강조할 부분)

| 주제 | 직접 채우는 ★★★ 자리 |
|---|---|
| 1 무대 | `"My Game"`(값) · `bgcolor`(함수) · `600, 600`(값) |
| 2 거북이 | `"square"`(값) · `color`(함수) |
| 3 펜 | `100`×3(값) · `penup`(함수) |
| 4 좌표 | `0, -250`(값) · `setx`(함수) · `-100`(값) |
| 5 이동 | `100` · `90` · `100` (모두 값) |
'''


def _extract_code_lines(markdown: str) -> list[str]:
    """마크다운의 ```python 블록에서 코드 줄만 뽑아 순서대로 중복 없이 돌려준다.

    자리 연습은 한 줄씩 표시하므로(app.js가 공백을 하나로 합친다) 코드 블록을
    줄 단위로 나눈다. `import turtle`처럼 여러 주제에 반복되는 줄은 한 번만 남긴다.
    """
    lines: list[str] = []
    seen: set[str] = set()
    in_block = False
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if stripped.startswith('```'):
            in_block = stripped != '```'  # ```python 시작이면 True, 닫는 ```면 False
            continue
        if not in_block or not stripped:
            continue
        if stripped not in seen:
            seen.add(stripped)
            lines.append(stripped)
    return lines


def _extract_code_blocks(markdown: str) -> list[str]:
    """마크다운의 ```python 블록을 통째로(줄바꿈 유지) 순서대로 돌려준다.

    문단 연습용이다. 블록 안의 빈 줄은 뺀다 — 타자 연습에서 빈 줄(엔터만)
    입력은 번거롭기 때문이다. 들여쓰기는 그대로 둔다.
    """
    blocks: list[str] = []
    current: list[str] = []
    in_block = False
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if stripped.startswith('```'):
            if stripped != '```':          # ```python 시작
                in_block = True
                current = []
            else:                          # 닫는 ```
                in_block = False
                code = [line for line in current if line.strip()]
                if code:
                    blocks.append('\n'.join(code))
            continue
        if in_block:
            current.append(raw)
    return blocks


def _extract_words(code: str) -> list[str]:
    """코드에서 파이썬 식별자(키워드·함수명·변수명)만 순서대로 중복 없이 뽑는다.

    낱말 연습용이다. 따옴표 안 문자열("My Game" 등)과 숫자는 낱말이 아니므로
    먼저 제거한 뒤 식별자만 남긴다.
    """
    without_strings = re.sub(r'"[^"]*"|\'[^\']*\'', '', code)
    words: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r'[A-Za-z_][A-Za-z0-9_]*', without_strings):
        if token not in seen:
            seen.add(token)
            words.append(token)
    return words


# 내장 자리 연습 예제 목록. 교사 대시보드에서 활성 목록을 고르면 전환된다.
# 앞으로 목록을 추가하려면 여기에 항목을 더한다(id → {name, lines}).
EXAMPLE_SETS = {
    'turtle': {
        'name': '터틀 타이핑 예제',
        'description': '정보 15·16차 터틀 예제 코드를 한 줄씩',
        'lines': _extract_code_lines(TURTLE_SOURCE_MARKDOWN),
        'source_markdown': TURTLE_SOURCE_MARKDOWN,
    },
}

# 처음(교사가 아직 아무것도 안 바꿨을 때) 자리 연습이 쓰는 목록.
DEFAULT_EXAMPLE_SET = 'turtle'


# 낱말·문장·문단 연습은 자리 연습과 **같은 터틀 예제 5개**에서 만든다.
#   - 문단: 예제 5개의 완성 코드 블록 그대로
#   - 문장: 예제의 코드 한 줄들(자리 연습과 같은, 중복 없는 줄 목록)
#   - 낱말: 예제별로 등장하는 식별자(키워드·함수명)를 모은 줄
# 터틀 예제 원본(TURTLE_SOURCE_MARKDOWN)만 고치면 세 모드가 함께 따라온다.
_TURTLE_BLOCKS = _extract_code_blocks(TURTLE_SOURCE_MARKDOWN)

PRACTICE_TEXTS = {
    '낱말': [' '.join(_extract_words(block)) for block in _TURTLE_BLOCKS],
    '문장': _extract_code_lines(TURTLE_SOURCE_MARKDOWN),
    '문단': _TURTLE_BLOCKS,
}


def _choose(candidates: list[str], exclude: str | None) -> str:
    """직전과 다른 것을 우선해서 하나 고른다."""
    pool = [text for text in candidates if text != exclude] or candidates
    return random.choice(pool)


def build_practice_text(mode: str, exclude: str | None = None,
                        jari_lines: list[str] | None = None) -> str:
    """모드에 맞는 연습 텍스트를 하나 돌려준다.

    exclude: 직전에 사용한 텍스트. 가능하면 연속으로 같은 텍스트를 주지 않는다.
    jari_lines: 자리 연습에 쓸 예제 줄 목록. 없으면 기본 목록을 쓴다. 교사가
        고른 활성 목록을 catalog가 여기로 넘긴다.
    """
    if mode == '자리':
        lines = jari_lines or EXAMPLE_SETS[DEFAULT_EXAMPLE_SET]['lines']
        if not lines:
            raise KeyError('자리')
        return _choose(lines, exclude)

    texts = PRACTICE_TEXTS.get(mode, [])
    if not texts:
        raise KeyError(mode)
    return _choose(texts, exclude)
