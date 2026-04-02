from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import Question

Command = Literal["up", "down", "submit", "quit", "noop"]


@dataclass(slots=True)
class QuizState:
    question: Question
    selected_index: int = 0

    def move_up(self) -> None:
        self.selected_index = (self.selected_index - 1) % len(self.question.options)

    def move_down(self) -> None:
        self.selected_index = (self.selected_index + 1) % len(self.question.options)

    def is_correct(self) -> bool:
        return self.selected_index == self.question.answer_index


def apply_command(state: QuizState, command: Command) -> None:
    if command == "up":
        state.move_up()
    elif command == "down":
        state.move_down()
