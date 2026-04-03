from __future__ import annotations

from typing import Literal

from .models import QuizState

Command = Literal["up", "down", "submit", "quit", "noop"]
