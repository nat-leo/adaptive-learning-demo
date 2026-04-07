<img width="533" height="215" alt="Screenshot 2026-04-07 at 9 25 29 AM" src="https://github.com/user-attachments/assets/37d2ad36-04ea-4628-8475-c2b7072b8382" />

# adaptive-learning-demo
A little cli tool for solving multiple choice questions.

- loads questions from `problems`, which contains many files containing JSON objects representing mulitple choice questions.
- Users move through answers with `↑` and `↓` or `j` and `k`
- User can submit the `>` selected question with `Enter`, and see if they got it right or wrong.

## Quick Start

Run the CLI:

```bash
adaptive-learning
```

## Question format

Questions are stored as a JSON array:

```json
[
  {
    "prompt": "Which keyword defines a function in Python?",
    "answers": ["func", "define", "def", "lambda"],
    "correct_answer": "def",
    "rating": 23
  }
]
```

## Run it

Install in editable mode:

```bash
python3.13 -m pip install -e .
```

Install test dependencies:

```bash
python3.13 -m pip install -e ".[test]"
```

Run the CLI:

```bash
adaptive-learning
```

Or run it directly with a custom question file:

```bash
python3.13 -m adaptive_learning practice.json
```

Run the test suite:

```bash
python3.13 -m pytest
```

## The Design
This project now uses an MVC architecture:

- Model: [`src/adaptive_learning/models.py`](src/adaptive_learning/models.py) and [`src/adaptive_learning/quiz.py`](src/adaptive_learning/quiz.py) define question data, quiz state, and state transitions.
- View: [`src/adaptive_learning/view.py`](src/adaptive_learning/view.py) handles terminal input, rendering, redraw behavior, and user-facing feedback text.
- Controller: [`src/adaptive_learning/controller.py`](src/adaptive_learning/controller.py) owns quiz flow (looping questions, applying commands, scoring, and quit/submit branching).
- Bootstrap: [`src/adaptive_learning/cli.py`](src/adaptive_learning/cli.py) wires data loading to the controller and preserves CLI entrypoint compatibility.
