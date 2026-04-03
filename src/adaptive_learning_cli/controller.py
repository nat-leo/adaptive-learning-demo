from __future__ import annotations

from .models import Question, QuizState
from .quiz import apply_command
from .view import TerminalView


class QuizController:
    def __init__(self, *, questions: list[Question], view: TerminalView) -> None:
        self._questions = questions
        self._view = view

    def run(self) -> int:
        score = 0
        total_questions = len(self._questions)

        with self._view:
            for number, question in enumerate(self._questions, start=1):
                state = QuizState(question=question)

                while True:
                    self._view.render_question(
                        state,
                        question_number=number,
                        total_questions=total_questions,
                    )
                    command = self._view.read_command()

                    if command == "quit":
                        self._view.clear_screen()
                        self._view.show_early_exit(score, total_questions)
                        return 1

                    if command == "submit":
                        break

                    apply_command(state, command)

                if state.is_correct():
                    score += 1

                self._view.render_question(
                    state,
                    question_number=number,
                    total_questions=total_questions,
                )
                self._view.render_feedback(state)
                if not self._view.wait_for_submit_or_quit():
                    self._view.clear_screen()
                    self._view.show_early_exit(score, total_questions)
                    return 1

        self._view.clear_screen()
        self._view.show_final_score(score, total_questions)
        return 0
