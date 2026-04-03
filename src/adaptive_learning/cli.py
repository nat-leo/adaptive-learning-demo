from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]

if __package__ in {None, ""}:
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))

    import adaptive_learning.data as data
    from adaptive_learning.controller import QuizController
    from adaptive_learning.models import QuizState, Command
    from adaptive_learning.view import (
        TerminalView,
        draw_frame as _draw_frame,
        ensure_interactive_terminal as _ensure_interactive_terminal,
        read_key as _read_key,
        render_screen as _render_screen,
    )
else:
    from . import data
    from .controller import QuizController
    from .models import QuizState, Command
    from .view import (
        TerminalView,
        draw_frame as _draw_frame,
        ensure_interactive_terminal as _ensure_interactive_terminal,
        read_key as _read_key,
        render_screen as _render_screen,
    )


def clear_screen() -> None:
    TerminalView().clear_screen()


def ensure_interactive_terminal() -> None:
    _ensure_interactive_terminal(sys.stdin, sys.stdout)


def render_screen(
    question: str,
    answers: list[str],
    selected_index: int,
    *,
    question_number: int = 1,
    total_questions: int = 1,
) -> str:
    return _render_screen(
        question=question,
        answers=answers,
        selected_index=selected_index,
        question_number=question_number,
        total_questions=total_questions,
    )


def draw_frame(stdout: object, frame: str) -> None:
    _draw_frame(stdout, frame)


def read_key() -> Command:
    return _read_key(sys.stdin)


def render_question(state: QuizState, question_number: int, total_questions: int) -> None:
    TerminalView().render_question(
        state,
        question_number=question_number,
        total_questions=total_questions,
    )


def render_feedback(state: QuizState) -> None:
    TerminalView().render_feedback(state)


def wait_for_enter() -> bool:
    return TerminalView().wait_for_submit_or_quit()


def problem_files() -> list[Path]:
    return sorted((SRC_ROOT / "db" / "problems").glob("*.json"))


def run_quiz() -> int:
    questions = data.load_from_many(problem_files())
    controller = QuizController(questions=questions, view=TerminalView())
    return controller.run()


def main() -> int:
    try:
        return run_quiz()
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 2
    except ValueError as error:
        print(f"Invalid question file: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
