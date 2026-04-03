from __future__ import annotations

from adaptive_learning.models import Question, QuizState


def _sample_question() -> Question:
    return Question(
        id="quiz-state-1",
        prompt="Which protocol is connectionless?",
        answers=["TCP", "UDP", "ARP"],
        correct_answer="UDP",
        rating=25,
    )


def test_selected_index_defaults_to_zero() -> None:
    state = QuizState(question=_sample_question())
    assert state.selected_index == 0


def test_move_down_increments_selected_index() -> None:
    state = QuizState(question=_sample_question())
    state.move_down()
    assert state.selected_index == 1


def test_move_down_wraps_to_zero_from_last_answer() -> None:
    state = QuizState(question=_sample_question(), selected_index=2)
    state.move_down()
    assert state.selected_index == 0


def test_move_up_wraps_to_last_answer_from_zero() -> None:
    state = QuizState(question=_sample_question(), selected_index=0)
    state.move_up()
    assert state.selected_index == 2


def test_move_up_decrements_selected_index() -> None:
    state = QuizState(question=_sample_question(), selected_index=2)
    state.move_up()
    assert state.selected_index == 1


def test_is_correct_is_false_when_selected_answer_is_not_correct() -> None:
    state = QuizState(question=_sample_question(), selected_index=0)
    assert state.is_correct() is False


def test_is_correct_is_true_when_selected_answer_matches_correct_answer() -> None:
    state = QuizState(question=_sample_question(), selected_index=1)
    assert state.is_correct() is True


def test_is_correct_reflects_navigation_changes() -> None:
    state = QuizState(question=_sample_question(), selected_index=0)
    assert state.is_correct() is False
    state.move_down()
    assert state.is_correct() is True
