from __future__ import annotations

import random
from datetime import datetime

from .models import (
    Command,
    IncorrectQuestion,
    Question,
    QuizState,
    SessionData,
    User,
)
from .view import TerminalView


def apply_command(state: QuizState, command: Command) -> None:
    if command == "up":
        state.move_up()
    elif command == "down":
        state.move_down()


def simple_backoff(reintroduciton_streak: int) -> int | None:
    """
    Intentionally inverted vs classic SRS:
    more misses/reintroductions -> shorter delay -> question appears sooner.

    Returns an integer being the minimum number of problems that must be attempted
    before the problem can be reintroduced. Streaks only last until 6 before the incorrect
    question can be deleted.
    """
    streak = [2, 4, 8, 16, 32, 64]
    if reintroduciton_streak >= len(streak):
        raise ValueError(f"simple_backoff(): the streak is {reintroduciton_streak}, max streak is {len(streak)}. Past that the user has correct their mistakes.")

    return streak[reintroduciton_streak]


def _question_category(question: Question) -> str:
    if question.rating <= 33:
        return "easy"
    if question.rating <= 66:
        return "medium"
    return "hard"


class QuizController:
    def __init__(self, *, questions: list[Question], view: TerminalView, user: User | None = None) -> None:
        self.questions = sorted(questions, key=lambda question: question.rating)
        self._view = view
        self.user = User() if user is None else user
        self._session_id = datetime.now().isoformat()
        if self._session_id not in self.user.sessions:
            self.user.sessions[self._session_id] = SessionData(
                session_id=self._session_id,
                started_at=datetime.now(),
            )
        self.score = {
            "correct": 0,
            "attempted": 0
        }

    def _record_attempt(self, question: Question, *, is_correct: bool) -> None:
        session = self.user.sessions[self._session_id]

        tracked = self.user.incorrect_questions.get(question.id)
        if tracked is not None:
            tracked.mark_reintroduced()

        if is_correct:
            self.score["correct"] += 1
            if tracked is not None:
                tracked.resolve()
            session.questions_correct += 1
            self.user.score += 1
        else:
            if tracked is None:
                tracked = IncorrectQuestion(
                    question_id=question.id,
                    category=_question_category(question),
                )
                self.user.incorrect_questions[question.id] = tracked
            tracked.mark_wrong()
            tracked.schedule_next(simple_backoff)

        self.score["attempted"] += 1
        session.questions_seen += 1
        self.user.attempts += 1

    def next_question(self, incorrect: IncorrectQuestion) -> Question:
        number = random.randint(0, len(self.questions) - 1)
        return self.questions[number]

    def run(self) -> int:
        with self._view:
            number = 0
            while number < len(self.questions):
                question = self.next_question(number)
                state = QuizState(question=question)
                while True:
                    self._view.render_question(
                        state,
                        number_correct=self.score["correct"],
                        total_questions=self.score["attempted"],
                    )
                    command = self._view.read_command()

                    if command == "quit":
                        self._view.clear_screen()
                        self._view.show_session(
                            self.user.sessions[self._session_id],
                            total_score=self.user.score,
                            total_attempts=self.user.attempts,
                        )
                        self._view.show_incorrect_questions(self.user.incorrect_questions)
                        self._view.show_early_exit(self.score["correct"], self.score["attempted"])
                        return 1

                    if command == "submit":
                        break

                    apply_command(state, command)

                self._record_attempt(question, is_correct=state.is_correct())

                self._view.render_question(
                    state,
                    number_correct=self.score["correct"],
                    total_questions=self.score["attempted"],
                )
                self._view.render_feedback(state)
                if not self._view.wait_for_submit_or_quit():
                    self._view.clear_screen()
                    self._view.show_session(
                        self.user.sessions[self._session_id],
                        total_score=self.user.score,
                        total_attempts=self.user.attempts,
                    )
                    self._view.show_incorrect_questions(self.user.incorrect_questions)
                    self._view.show_early_exit(self.score["correct"], self.score["attempted"])
                    return 1

                number += 1

        self._view.clear_screen()
        self._view.show_session(
            self.user.sessions[self._session_id],
            total_score=self.user.score,
            total_attempts=self.user.attempts,
        )
        self._view.show_incorrect_questions(self.user.incorrect_questions)
        self._view.show_final_score(self.score["correct"], self.score["attempted"])
        return 0
