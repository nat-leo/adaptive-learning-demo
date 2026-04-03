from __future__ import annotations

from typing import Literal

from .models import QuizState

Command = Literal["up", "down", "submit", "quit", "noop"]


def apply_command(state: QuizState, command: Command) -> None:
    if command == "up":
        state.move_up()
    elif command == "down":
        state.move_down()
