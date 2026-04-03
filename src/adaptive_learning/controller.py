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

        if is_correct:
            self.score["correct"] += 1
            if tracked is not None:
                tracked.mark_reintroduced()
                tracked.schedule_next()
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

        for key, iq in self.user.incorrect_questions.items():
            iq.mark_passed()

        self.score["attempted"] += 1
        session.questions_seen += 1
        self.user.attempts += 1

    def select_question_by_id(self, id: str) -> Question:
        for q in self.questions:
            if q.id == id:
                return q
        raise IndexError(f"select_question_by_id(): id={id} not found in question bank.")


    def next_question(self) -> Question:
        if len(self.user.incorrect_questions) > 0:
            for key_id, iq in self.user.incorrect_questions.items():
                if iq.last_seen >= iq.due_in:
                    return self.select_question_by_id(key_id)
                else:
                    return random.choice(self.questions)
        return random.choice(self.questions)


    def run(self) -> int:
        with self._view:
            number = 0
            while number < len(self.questions):
                question = self.next_question()
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
