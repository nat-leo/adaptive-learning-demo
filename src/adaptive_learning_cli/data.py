from __future__ import annotations

import json
from pathlib import Path

from .models import Question

DEFAULT_QUESTIONS = [
    Question(
        prompt="Which data structure uses first-in, first-out ordering?",
        answers=["Queue", "Tree", "Set"],
        correct_answer="Stack",
        rating=5
    )
]

def load_from_many(paths: list[Path] | None = None) -> list[Question]:
    if paths is None:
        return list(DEFAULT_QUESTIONS)

    questions: list[Question] = []
    for path in paths:
        questions.extend(load_questions(path))

    return questions

def load_questions(path: Path | None = None) -> list[Question]:
    if path is None:
        return list(DEFAULT_QUESTIONS)

    if not path.exists():
        raise FileNotFoundError(f"Question file not found: {path}")

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return list(DEFAULT_QUESTIONS)

    payload = json.loads(content)
    if not isinstance(payload, list):
        raise ValueError("Question file must contain a JSON array.")

    questions = [Question.from_dict(item) for item in payload]
    if not questions:
        raise ValueError("Question file must contain at least one question.")

    return questions
