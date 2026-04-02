# adaptive-learning-demo
A little cli tool for solving multiple choice questions.

## Python 3.13 scaffold

This repository now includes a small Python 3.13 CLI scaffold that:

- loads questions from `practice.json`
- lets the user move through answers with `↑` and `↓` or `j` and `k`
- submits the current selection with `Enter`

## Question format

Questions are stored as a JSON array:

```json
[
  {
    "prompt": "Which keyword defines a function in Python?",
    "options": ["func", "define", "def", "lambda"],
    "correct_answer": "def"
  }
]
```

The loader also accepts the older `problem` / `answers` field names and can still read `answer_index` if you prefer index-based answers.

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
