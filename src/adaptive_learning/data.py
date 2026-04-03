from __future__ import annotations

import json
from pathlib import Path

from .models import Question

DEFAULT_QUESTIONS = [
    Question(
        id="default-1",
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
    seen_ids: set[str] = set()
    for path in paths:
        loaded = load_questions(path)
        for question in loaded:
            if question.id in seen_ids:
                raise ValueError(f"Duplicate question id '{question.id}' found while loading {path}.")
            seen_ids.add(question.id)
            questions.append(question)

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

    seen_ids: set[str] = set()
    for question in questions:
        if question.id in seen_ids:
            raise ValueError(f"Question file contains duplicate id '{question.id}': {path}")
        seen_ids.add(question.id)

    return questions
