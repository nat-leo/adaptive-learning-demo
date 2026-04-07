from __future__ import annotations

from datetime import datetime

import pytest

from adaptive_learning import __all__ as package_exports
from adaptive_learning.models import IncorrectQuestion, Question, QuizState, User


def test_package_exports_remain_stable() -> None:
    assert set(package_exports) == {
        "IncorrectQuestion",
        "Question",
        "QuizState",
        "SessionData",
        "User",
    }


@pytest.mark.parametrize("prompt_key", ["prompt", "problem"])
def test_question_from_dict_accepts_prompt_or_problem(prompt_key: str) -> None:
    raw = {
        "id": "q-1",
        prompt_key: "What does DNS do?",
        "answers": ["Resolves names", "Routes packets"],
        "correct_answer": "Resolves names",
        "rating": 25,
    }

    question = Question.from_dict(raw)

    assert question.id == "q-1"
    assert question.prompt == "What does DNS do?"
    assert question.correct_answer == "Resolves names"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ({"prompt": "p", "answers": ["a", "b"], "correct_answer": "a", "rating": 1}, "Question 'id'"),
        ({"id": "q", "answers": ["a", "b"], "correct_answer": "a", "rating": 1}, "Question 'prompt'"),
        ({"id": "q", "prompt": "p", "answers": ["a"], "correct_answer": "a", "rating": 1}, "at least two"),
        ({"id": "q", "prompt": "p", "answers": ["a", ""], "correct_answer": "a", "rating": 1}, "Each option"),
        ({"id": "q", "prompt": "p", "answers": ["a", "b"], "rating": 1}, "correct_answer"),
        ({"id": "q", "prompt": "p", "answers": ["a", "b"], "correct_answer": "a", "rating": 101}, "between 1 and 100"),
        ({"id": "q", "prompt": "p", "answers": ["a", "b"], "correct_answer": "a", "rating": "1"}, "between 1 and 100"),
    ],
)
def test_question_from_dict_rejects_invalid_payloads(raw: dict[str, object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        Question.from_dict(raw)


def test_quiz_state_navigation_wraps_and_correctness_tracks_selection() -> None:
    question = Question(
        id="q-state",
        prompt="Which protocol is connectionless?",
        answers=["TCP", "UDP", "ARP"],
        correct_answer="UDP",
        rating=20,
    )
    state = QuizState(question=question)

    assert state.is_correct() is False
    state.move_down()
    assert state.selected_index == 1
    assert state.is_correct() is True
    state.move_down()
    state.move_down()
    assert state.selected_index == 0
    state.move_up()
    assert state.selected_index == 2


def test_incorrect_question_lifecycle_and_backoff_schedule() -> None:
    item = IncorrectQuestion(question_id="q-1", category="easy")

    item.mark_wrong()
    assert item.times_wrong == 1
    assert item.last_seen == 0
    assert item.reintroduction_streak == 0

    item.mark_passed()
    assert item.last_seen == 1

    item.mark_reintroduced()
    assert item.reintroduction_streak == 1
    assert item.times_seen_since_wrong == 1
    assert item.last_seen == 0

    item.schedule_next()
    assert item.due_in == 4

    item.reintroduction_streak = 5
    item.schedule_next()
    assert item.due_in == 64

    item.reintroduction_streak = 6
    item.schedule_next()
    assert item.due_in is None


def test_incorrect_question_from_dict_reflects_current_deserialization_behavior() -> None:
    loaded = IncorrectQuestion.from_dict(
        {
            "question_id": "q-2",
            "category": "medium",
            "last_seen": "2026-04-01T10:00:00",
            "due_in": 0,
            "times_wrong": 3,
            "times_seen_since_wrong": 2,
            "reintroduction_streak": 1,
        }
    )

    # This test intentionally documents current behavior, including the 0->None conversion.
    assert isinstance(loaded.last_seen, datetime)
    assert loaded.due_in is None
    assert loaded.times_wrong == 3


def test_user_from_dict_parses_sessions_and_incorrect_pool() -> None:
    user = User.from_dict(
        {
            "score": 5,
            "attempts": 9,
            "sessions": {
                "s1": {
                    "session_id": "s1",
                    "started_at": "2026-04-01T09:00:00",
                    "questions_seen": 4,
                    "questions_correct": 3,
                }
            },
            "incorrect_questions": {
                "q-3": {
                    "question_id": "q-3",
                    "category": "hard",
                    "last_seen": "2026-04-01T11:00:00",
                    "due_in": 4,
                    "times_wrong": 2,
                }
            },
        }
    )

    assert user.score == 5
    assert user.attempts == 9
    assert user.sessions["s1"].questions_correct == 3
    assert "q-3" in user.incorrect_questions
