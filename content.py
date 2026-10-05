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


# 두 번째 예제 「주인공 이동하기」. 방향키(←·→)로 네모 주인공을 좌우로 움직이는
# **하나의 완성 프로그램**이다. 문단 연습이 늘 완성 코드 전체(방향키 연결 포함)를
# 보여주도록 코드 블록을 하나로 둔다. 쪼개 두면 문단이 조각(프리픽스)만 보여 줘
# 방향키 연결 부분이 안 나오는 문제가 있었다.
# (한글 주석은 연습 입력이 한글을 막으므로 코드 블록에 넣지 않는다.)
TURTLE_MOVE_SOURCE_MARKDOWN = '''# 파이썬 타자 도우미 — 터틀 예제 2 「주인공 이동하기」 (정답)

방향키(←·→)로 네모 주인공을 좌우로 움직이는 완성 코드입니다.

---

## 완성 코드

```python
import turtle

screen = turtle.Screen()
screen.setup(400, 500)

player = turtle.Turtle()
player.shape("square")
player.penup()
player.goto(0, -200)

def go_left():
    x = player.xcor()
    player.setx(x - 20)

def go_right():
    x = player.xcor()
    player.setx(x + 20)

screen.listen()
screen.onkeypress(go_left, "Left")
screen.onkeypress(go_right, "Right")

screen.mainloop()
```

---

## 참고: 빈칸(★★★) 자리 (타자 도우미에서 강조할 부분)

| 부분 | 직접 채우는 ★★★ 자리 |
|---|---|
| 무대 | `400, 500`(값) |
| 주인공 | `"square"`(값) · `penup`(함수) · `0, -200`(값) |
| 이동 함수 | `xcor`(함수) · `setx`(함수) · `20`(값) |
| 키 연결 | `listen`(함수) · `onkeypress`(함수) · `"Left"` · `"Right"`(값) |
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


def _build_example_set(name: str, description: str, source_markdown: str) -> dict:
    """예제 원본 마크다운 하나에서 네 모드가 쓸 텍스트를 모두 파생한다.

      - lines : 코드 한 줄들(중복 없이). 자리·문장 연습이 쓴다.
      - blocks: ```python 블록 전체. 문단 연습이 쓴다.
      - words : 블록별 식별자(키워드·함수명)를 모은 줄. 낱말 연습이 쓴다.
    원본(source_markdown) 하나만 고치면 네 모드가 함께 따라온다.
    """
    blocks = _extract_code_blocks(source_markdown)
    return {
        'name': name,
        'description': description,
        'source_markdown': source_markdown,
        'lines': _extract_code_lines(source_markdown),
        'blocks': blocks,
        'words': [' '.join(_extract_words(block)) for block in blocks],
    }


# 내장 예제 목록. 교사 대시보드에서 활성 목록을 고르면 네 모드가 모두 전환된다.
# 앞으로 목록을 추가하려면 여기에 _build_example_set(...) 항목을 더한다.
EXAMPLE_SETS = {
    'turtle': _build_example_set(
        '터틀 타이핑 예제',
        '정보 15·16차 터틀 예제 코드(주제1~5)',
        TURTLE_SOURCE_MARKDOWN,
    ),
    'turtle_move': _build_example_set(
        '터틀 예제 2 · 주인공 이동하기',
        '방향키로 주인공을 움직이는 완성 터틀 프로그램',
        TURTLE_MOVE_SOURCE_MARKDOWN,
    ),
}

# 처음(교사가 아직 아무것도 안 바꿨을 때) 쓰는 예제 목록.
DEFAULT_EXAMPLE_SET = 'turtle'


# 모드별로 예제 세트의 어떤 파생 텍스트를 쓰는지.
# 자리·문장은 코드 한 줄, 문단은 블록 전체, 낱말은 식별자 줄.
_MODE_TEXT_KEY = {
    '자리': 'lines',
    '문장': 'lines',
    '문단': 'blocks',
    '낱말': 'words',
}


def texts_for_mode(example_set: dict, mode: str) -> list[str]:
    """예제 세트에서 해당 모드가 쓸 후보 텍스트 목록을 돌려준다."""
    key = _MODE_TEXT_KEY.get(mode)
    if key is None:
        raise KeyError(mode)
    return example_set[key]


# 기본 예제 세트에서 파생한 낱말·문장·문단 텍스트(하위 호환·직접 참조용).
PRACTICE_TEXTS = {
    mode: texts_for_mode(EXAMPLE_SETS[DEFAULT_EXAMPLE_SET], mode)
    for mode in ('낱말', '문장', '문단')
}


def _choose(candidates: list[str], exclude: str | None) -> str:
    """직전과 다른 것을 우선해서 하나 고른다."""
    pool = [text for text in candidates if text != exclude] or candidates
    return random.choice(pool)


def build_practice_text(mode: str, exclude: str | None = None,
                        texts: list[str] | None = None) -> str:
    """모드에 맞는 연습 텍스트를 하나 돌려준다.

    exclude: 직전에 사용한 텍스트. 가능하면 연속으로 같은 텍스트를 주지 않는다.
    texts: 이 모드가 쓸 후보 목록. 없으면 기본 예제 세트에서 파생한 것을 쓴다.
        교사가 고른 활성 예제 세트의 텍스트를 catalog가 여기로 넘긴다.
    """
    if texts is None:
        texts = texts_for_mode(EXAMPLE_SETS[DEFAULT_EXAMPLE_SET], mode)
    if not texts:
        raise KeyError(mode)
    return _choose(texts, exclude)
