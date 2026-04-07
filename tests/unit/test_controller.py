from __future__ import annotations

import pytest

import adaptive_learning.controller as controller
from adaptive_learning.controller import QuizController, _question_category, apply_command
from adaptive_learning.models import IncorrectQuestion, Question, QuizState


def _question(question_id: str, *, rating: int, correct_answer: str = "A") -> Question:
    return Question(
        id=question_id,
        prompt=f"Prompt {question_id}",
        answers=["A", "B", "C"],
        correct_answer=correct_answer,
        rating=rating,
    )


class FakeView:
    def __init__(self, *, commands: list[str], wait_results: list[bool] | None = None) -> None:
        self.commands = list(commands)
        self.wait_results = [] if wait_results is None else list(wait_results)

        self.entered = False
        self.exited = False
        self.cleared = 0

        self.render_calls: list[tuple[str, int, int, int]] = []
        self.feedback_calls = 0
        self.session_calls: list[tuple[int, int]] = []
        self.incorrect_calls = 0
        self.early_exit_calls: list[tuple[int, int]] = []
        self.final_score_calls: list[tuple[int, int]] = []

    def __enter__(self) -> "FakeView":
        self.entered = True
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.exited = True

    def render_question(self, state: QuizState, number_correct: int, total_questions: int) -> None:
        self.render_calls.append((state.question.id, state.selected_index, number_correct, total_questions))

    def read_command(self) -> str:
        if not self.commands:
            return "submit"
        return self.commands.pop(0)

    def render_feedback(self, state: QuizState) -> None:
        self.feedback_calls += 1

    def wait_for_submit_or_quit(self) -> bool:
        if not self.wait_results:
            return True
        return self.wait_results.pop(0)

    def clear_screen(self) -> None:
        self.cleared += 1

    def show_session(self, session, *, total_score: int | None = None, total_attempts: int | None = None) -> None:
        self.session_calls.append((total_score or 0, total_attempts or 0))

    def show_incorrect_questions(self, incorrect_questions) -> None:
        self.incorrect_calls += 1

    def show_early_exit(self, score: int, total_questions: int) -> None:
        self.early_exit_calls.append((score, total_questions))

    def show_final_score(self, score: int, total_questions: int) -> None:
        self.final_score_calls.append((score, total_questions))


def test_apply_command_moves_state_only_for_navigation_commands() -> None:
    state = QuizState(question=_question("q1", rating=10), selected_index=0)

    apply_command(state, "up")
    assert state.selected_index == 2

    apply_command(state, "down")
    assert state.selected_index == 0

    apply_command(state, "noop")
    assert state.selected_index == 0


@pytest.mark.parametrize(
    "rating,expected",
    [
        (1, "easy"),
        (33, "easy"),
        (34, "medium"),
        (66, "medium"),
        (67, "hard"),
    ],
)
def test_question_category_thresholds(rating: int, expected: str) -> None:
    assert _question_category(_question("q", rating=rating)) == expected


def test_record_attempt_wrong_then_correct_updates_user_and_retry_pool() -> None:
    question = _question("q-record", rating=20, correct_answer="B")
    quiz = QuizController(questions=[question], view=FakeView(commands=[]))

    quiz._record_attempt(question, is_correct=False)

    tracked = quiz.user.incorrect_questions[question.id]
    assert tracked.category == "easy"
    assert tracked.times_wrong == 1
    assert tracked.last_seen == 1
    assert quiz.user.score == 0
    assert quiz.user.attempts == 1

    quiz._record_attempt(question, is_correct=True)

    assert tracked.reintroduction_streak == 1
    assert tracked.times_seen_since_wrong == 1
    assert tracked.due_in == 4
    assert tracked.last_seen == 1
    assert quiz.user.score == 1
    assert quiz.user.attempts == 2


def test_next_question_returns_due_retry_question_first() -> None:
    questions = [_question("q1", rating=10), _question("q2", rating=30)]
    quiz = QuizController(questions=questions, view=FakeView(commands=[]))
    quiz.user.incorrect_questions["q2"] = IncorrectQuestion(
        question_id="q2",
        category="easy",
        last_seen=2,
        due_in=2,
    )

    chosen = quiz.next_question()

    assert chosen.id == "q2"


def test_next_question_uses_random_pool_when_retry_item_is_not_due(monkeypatch: pytest.MonkeyPatch) -> None:
    questions = [_question("q1", rating=10), _question("q2", rating=30)]
    quiz = QuizController(questions=questions, view=FakeView(commands=[]))
    quiz.user.incorrect_questions["q1"] = IncorrectQuestion(
        question_id="q1",
        category="easy",
        last_seen=0,
        due_in=3,
    )

    monkeypatch.setattr(controller.random, "choice", lambda seq: seq[-1])

    chosen = quiz.next_question()
    assert chosen.id == "q2"


def test_next_question_raises_if_retry_question_id_is_missing_from_bank() -> None:
    quiz = QuizController(questions=[_question("q1", rating=10)], view=FakeView(commands=[]))
    quiz.user.incorrect_questions["missing"] = IncorrectQuestion(
        question_id="missing",
        category="hard",
        last_seen=3,
        due_in=1,
    )

    with pytest.raises(IndexError, match="not found"):
        quiz.next_question()


def test_run_returns_one_when_user_quits_on_question_screen() -> None:
    view = FakeView(commands=["quit"])
    quiz = QuizController(questions=[_question("q1", rating=10)], view=view)

    code = quiz.run()

    assert code == 1
    assert view.entered and view.exited
    assert view.cleared == 1
    assert view.early_exit_calls == [(0, 0)]
    assert view.final_score_calls == []


def test_run_returns_one_when_user_quits_on_feedback_screen() -> None:
    view = FakeView(commands=["submit"], wait_results=[False])
    quiz = QuizController(questions=[_question("q1", rating=10, correct_answer="A")], view=view)

    code = quiz.run()

    assert code == 1
    assert view.feedback_calls == 1
    assert view.early_exit_calls == [(1, 1)]
    assert view.final_score_calls == []


def test_run_returns_zero_and_shows_final_score_after_full_quiz(monkeypatch: pytest.MonkeyPatch) -> None:
    view = FakeView(commands=["submit", "submit"], wait_results=[True, True])
    questions = [_question("q1", rating=40, correct_answer="A"), _question("q2", rating=5, correct_answer="A")]

    monkeypatch.setattr(controller.random, "choice", lambda seq: seq[0])

    quiz = QuizController(questions=questions, view=view)
    code = quiz.run()

    session = quiz.user.sessions[quiz._session_id]

    assert code == 0
    assert view.final_score_calls == [(2, 2)]
    assert view.early_exit_calls == []
    assert session.questions_seen == 2
    assert session.questions_correct == 2
    assert quiz.user.attempts == 2
    assert quiz.user.score == 2
