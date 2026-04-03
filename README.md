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
python3.13 -m adaptive_learning_cli practice.json
```

Run the test suite:

```bash
python3.13 -m pytest
```

## The Design
This project now uses an MVC architecture:

- Model: [`src/adaptive_learning_cli/models.py`](src/adaptive_learning_cli/models.py) and [`src/adaptive_learning_cli/quiz.py`](src/adaptive_learning_cli/quiz.py) define question data, quiz state, and state transitions.
- View: [`src/adaptive_learning_cli/view.py`](src/adaptive_learning_cli/view.py) handles terminal input, rendering, redraw behavior, and user-facing feedback text.
- Controller: [`src/adaptive_learning_cli/controller.py`](src/adaptive_learning_cli/controller.py) owns quiz flow (looping questions, applying commands, scoring, and quit/submit branching).
- Bootstrap: [`src/adaptive_learning_cli/cli.py`](src/adaptive_learning_cli/cli.py) wires data loading to the controller and preserves CLI entrypoint compatibility.
