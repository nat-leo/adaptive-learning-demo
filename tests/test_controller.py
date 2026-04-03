from __future__ import annotations

import pytest

from adaptive_learning.controller import QuizController
from adaptive_learning.models import Question
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
