from __future__ import annotations

import json
from pathlib import Path

import pytest

from adaptive_learning import data
from adaptive_learning.cli import problem_files


def _write_questions(path: Path, payload: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_questions_requires_id(tmp_path: Path) -> None:
    question_file = tmp_path / "questions.json"
    _write_questions(
        question_file,
        [
            {
                "prompt": "What is TCP?",
                "answers": ["A protocol", "A router"],
                "correct_answer": "A protocol",
                "rating": 15,
            }
        ],
    )

    with pytest.raises(ValueError, match="Question 'id' must be a non-empty string."):
        data.load_questions(question_file)


def test_load_questions_rejects_duplicate_ids_in_same_file(tmp_path: Path) -> None:
    question_file = tmp_path / "questions.json"
    _write_questions(
        question_file,
        [
            {
                "id": "dup-1",
                "prompt": "Q1",
                "answers": ["A", "B"],
                "correct_answer": "A",
                "rating": 10,
            },
            {
                "id": "dup-1",
                "prompt": "Q2",
                "answers": ["C", "D"],
                "correct_answer": "C",
                "rating": 20,
            },
        ],
    )

    with pytest.raises(ValueError, match="duplicate id 'dup-1'"):
        data.load_questions(question_file)


def test_load_from_many_rejects_duplicate_ids_across_files(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    _write_questions(
        first,
        [
            {
                "id": "shared-1",
                "prompt": "Q1",
                "answers": ["A", "B"],
                "correct_answer": "A",
                "rating": 30,
            }
        ],
    )
    _write_questions(
        second,
        [
            {
                "id": "shared-1",
                "prompt": "Q2",
                "answers": ["C", "D"],
                "correct_answer": "C",
                "rating": 40,
            }
        ],
    )

    with pytest.raises(ValueError, match="Duplicate question id 'shared-1'"):
        data.load_from_many([first, second])


def test_problem_bank_has_unique_non_empty_ids() -> None:
    questions = data.load_from_many(problem_files())
    ids = [question.id for question in questions]
    assert ids
    assert all(ids)
    assert len(ids) == len(set(ids))
