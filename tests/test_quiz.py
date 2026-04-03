from __future__ import annotations

import json
from pathlib import Path

from adaptive_learning_cli.controller import apply_command
from adaptive_learning_cli.data import load_questions
from adaptive_learning_cli.models import Question
from adaptive_learning_cli.quiz import QuizState


def test_move_down_advances_selection() -> None:
    state = QuizState(
        question=Question(
            prompt="Prompt",
            answers=["A", "B", "C"],
            correct_answer=1,
        )
    )

    apply_command(state, "down")

    assert state.selected_index == 1


def test_move_up_wraps_to_last_option() -> None:
    state = QuizState(
        question=Question(
            prompt="Prompt",
            answers=["A", "B", "C"],
            correct_answer=1,
        )
    )

    apply_command(state, "up")

    assert state.selected_index == 2


def test_load_questions_reads_json_array(tmp_path: Path) -> None:
    payload = [
        {
            "prompt": "What is 2 + 2?",
            "answers": ["3", "4", "5"],
            "correct_answer": "4",
        }
    ]

    file_path = tmp_path / "questions.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    questions = load_questions(file_path)

    assert len(questions) == 1
    assert questions[0].prompt == "What is 2 + 2?"
    assert questions[0].correct_answer == 1


def test_load_questions_accepts_legacy_question_keys(tmp_path: Path) -> None:
    payload = [
        {
            "problem": "Which protocol is connectionless?",
            "answers": ["TCP", "UDP", "ICMP"],
            "correct_answer": "UDP",
        }
    ]

    file_path = tmp_path / "questions.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    questions = load_questions(file_path)

    assert len(questions) == 1
    assert questions[0].prompt == "Which protocol is connectionless?"
    assert questions[0].answers == ["TCP", "UDP", "ICMP"]
    assert questions[0].correct_answer == 1


def test_load_questions_uses_default_for_empty_file(tmp_path: Path) -> None:
    file_path = tmp_path / "questions.json"
    file_path.write_text("", encoding="utf-8")

    questions = load_questions(file_path)

    assert len(questions) == 1
