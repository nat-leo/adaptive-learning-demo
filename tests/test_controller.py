from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import adaptive_learning.controller as controller
from adaptive_learning.controller import QuizController
from adaptive_learning.models import Question, QuestionStatus
from adaptive_learning.view import TerminalView


@pytest.fixture
def unsorted_questions() -> list[Question]:
    return [
        Question(id="hard-1", prompt="Hard", answers=["A", "B"], correct_answer="B", rating=90),
        Question(id="easy-1", prompt="Easy", answers=["A", "B"], correct_answer="B", rating=10),
        Question(id="medium-1", prompt="Medium", answers=["A", "B"], correct_answer="B", rating=50),
    ]


@pytest.fixture
def quiz_controller(unsorted_questions: list[Question]) -> QuizController:
    return QuizController(questions=unsorted_questions, view=TerminalView())


def test_controller_sorts_questions_by_rating(quiz_controller: QuizController) -> None:
    ratings = [question.rating for question in quiz_controller.questions]
    assert ratings == sorted(ratings)


def test_exponential_backoff_scales_with_reintroductions(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = datetime(2026, 4, 3, 12, 0, 0)

    class FixedDateTime:
        @classmethod
        def now(cls) -> datetime:
            return fixed_now

    monkeypatch.setattr(controller, "datetime", FixedDateTime)

    due = controller.exponential_backoff(times_wrong=3, reintroduced_count=2)
    assert due == fixed_now + timedelta(minutes=12)


def test_record_attempt_tracks_wrong_and_resolve_flow() -> None:
    question = Question(
        id="net-1",
        prompt="Which protocol is connectionless?",
        answers=["TCP", "UDP", "ARP"],
        correct_answer="UDP",
        rating=20,
    )
    quiz_controller = QuizController(questions=[question], view=TerminalView())

    quiz_controller._record_attempt(question, is_correct=False)

    tracked = quiz_controller.user.incorrect_questions[question.id]
    assert tracked.times_wrong == 1
    assert tracked.next_due is not None
    assert tracked.status == QuestionStatus.ACTIVE
    assert quiz_controller.user.attempts == 1
    assert quiz_controller.user.score == 0

    quiz_controller._record_attempt(question, is_correct=True)

    assert tracked.reintroduced_count == 1
    assert tracked.status == QuestionStatus.MASTERED
    assert quiz_controller.user.attempts == 2
    assert quiz_controller.user.score == 1
