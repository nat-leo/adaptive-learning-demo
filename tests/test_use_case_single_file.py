from __future__ import annotations

from datetime import datetime

import pytest

from adaptive_learning.use_case_single_file import (
    IncorrectQuestion,
    SessionData,
    User,
    present_question,
    run_attempt,
    simple_backoff,
)


def test_simple_backoff_returns_expected_values() -> None:
    assert simple_backoff(0) == 2
    assert simple_backoff(1) == 4
    assert simple_backoff(2) == 8
    assert simple_backoff(5) == 64


def test_simple_backoff_raises_when_streak_is_too_high() -> None:
    with pytest.raises(ValueError, match="max streak is 6"):
        simple_backoff(6)


def test_run_attempt_correct_updates_score_and_session() -> None:
    user = User()
    session = SessionData(session_id="s1", started_at=datetime.now())
    user.sessions[session.session_id] = session

    run_attempt(user, session, "q1", "arrays", is_correct=True)

    assert user.score == 1
    assert user.attempts == 1
    assert session.questions_seen == 1
    assert session.questions_correct == 1
    assert "q1" not in user.incorrect_questions


def test_run_attempt_incorrect_creates_retry_item() -> None:
    user = User()
    session = SessionData(session_id="s1", started_at=datetime.now())

    run_attempt(user, session, "q2", "graphs", is_correct=False)

    item = user.incorrect_questions["q2"]
    assert user.score == 0
    assert user.attempts == 1
    assert session.questions_seen == 1
    assert session.questions_correct == 0
    assert item.category == "graphs"
    assert item.times_wrong == 1
    assert item.reintroduciton_streak == 0
    assert item.due_in == 2
    assert item.last_seen is not None


def test_run_attempt_repeat_incorrect_increments_times_wrong() -> None:
    user = User()
    session = SessionData(session_id="s1", started_at=datetime.now())

    run_attempt(user, session, "q3", "dp", is_correct=False)
    first_seen = user.incorrect_questions["q3"].last_seen
    run_attempt(user, session, "q3", "dp", is_correct=False)

    item = user.incorrect_questions["q3"]
    assert user.attempts == 2
    assert item.times_wrong == 2
    assert item.due_in == 2
    assert item.last_seen is not None
    assert first_seen is not None
    assert item.last_seen >= first_seen


def test_present_question_is_noop_without_retry_item() -> None:
    user = User()
    present_question(user, "missing")
    assert user.incorrect_questions == {}


def test_present_question_does_not_change_retry_item_currently() -> None:
    user = User(
        incorrect_questions={
            "q4": IncorrectQuestion(question_id="q4", category="trees")
        }
    )

    present_question(user, "q4")

    item = user.incorrect_questions["q4"]
    assert item.reintroduciton_streak == 0
    assert item.times_seen_since_wrong == 0
