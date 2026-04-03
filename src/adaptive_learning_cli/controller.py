from __future__ import annotations

from .models import Question, QuizState, Command
from .view import TerminalView


def apply_command(state: QuizState, command: Command) -> None:
    if command == "up":
        state.move_up()
    elif command == "down":
        state.move_down()


class QuizController:
    def __init__(self, *, questions: list[Question], view: TerminalView) -> None:
        self.questions = sorted(questions, key=lambda question: question.rating)
        self._view = view
        self.score = {
            "correct": 0,
            "attempted": 0
        }

    def run(self) -> int:
        with self._view:
            number = 0
            while number < len(self.questions):
                question = self.questions[number]
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
                        self._view.show_early_exit(self.score["correct"], self.score["attempted"])
                        return 1

                    if command == "submit":
                        break

                    apply_command(state, command)

                if state.is_correct():
                    self.score["correct"] += 1
                self.score["attempted"] += 1 

                self._view.render_question(
                    state,
                    number_correct=self.score["correct"],
                    total_questions=self.score["attempted"],
                )
                self._view.render_feedback(state)
                if not self._view.wait_for_submit_or_quit():
                    self._view.clear_screen()
                    self._view.show_early_exit(self.score["correct"], self.score["attempted"])
                    return 1

                number += 1

        self._view.clear_screen()
        self._view.show_final_score(self.score["correct"], self.score["attempted"])
        return 0


    # def run(self) -> int:
    #     with self._view:
    #         for number, question in enumerate(self.questions, start=1):
    #             state = QuizState(question=question)
    #             while True:
    #                 self._view.render_question(
    #                     state,
    #                     question_number=number,
    #                     total_questions=self.score["attempted"],
    #                 )
    #                 command = self._view.read_command()

    #                 if command == "quit":
    #                     self._view.clear_screen()
    #                     self._view.show_early_exit(self.score["correct"], self.score["attempted"])
    #                     return 1

    #                 if command == "submit":
    #                     break

    #                 apply_command(state, command)

    #             if state.is_correct():
    #                 self.score["correct"] += 1
    #             else:
    #                 self.score["attempts"] += 1 

    #             self._view.render_question(
    #                 state,
    #                 question_number=number,
    #                 total_questions=self.score["attempted"],
    #             )
    #             self._view.render_feedback(state)
    #             if not self._view.wait_for_submit_or_quit():
    #                 self._view.clear_screen()
    #                 self._view.show_early_exit(self.score["correct"], self.score["attempted"])
    #                 return 1

    #     self._view.clear_screen()
    #     self._view.show_final_score(self.score["correct"], self.score["attempted"])
    #     return 0
