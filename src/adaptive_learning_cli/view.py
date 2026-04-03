from __future__ import annotations

import os
import sys
import textwrap

from .models import QuizState, Command

if os.name == "nt":
    import msvcrt
else:
    import termios
    import tty

CLEAR_SCREEN = "\033[H\033[2J\033[3J"
HELP_TEXT = "Use ↑/↓ or j/k to move, Enter to submit, q to quit."


class RawTerminal:
    def __init__(self, stdin: object) -> None:
        self._stdin = stdin

    def __enter__(self) -> "RawTerminal":
        if os.name != "nt":
            fd = self._stdin.fileno()
            self._fd = fd
            self._old_settings = termios.tcgetattr(fd)
            # cbreak keeps character-at-a-time input without disabling
            # output newline processing (raw mode causes visual line drift).
            tty.setcbreak(fd)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if os.name != "nt":
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)


def ensure_interactive_terminal(stdin: object, stdout: object) -> None:
    stdin_is_tty = bool(getattr(stdin, "isatty", lambda: False)())
    stdout_is_tty = bool(getattr(stdout, "isatty", lambda: False)())
    if not stdin_is_tty or not stdout_is_tty:
        raise RuntimeError("adaptive-learning requires an interactive terminal.")


def render_screen(
    question: str,
    answers: list[str],
    selected_index: int,
    *,
    question_number: int = 1,
    total_questions: int = 1,
) -> str:
    content_width = 60
    question_lines = textwrap.wrap(
        question,
        width=content_width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [question]

    rendered_answers: list[str] = []
    for index, answer in enumerate(answers):
        prefix = "> " if index == selected_index else ""
        answer_width = max(1, content_width - len(prefix))
        answer_lines = answer.splitlines() or [answer]
        first_visual_line = True
        for answer_line in answer_lines:
            wrapped_answer_lines = textwrap.wrap(
                answer_line,
                width=answer_width,
                break_long_words=False,
                break_on_hyphens=False,
            ) or [answer_line]
            for wrapped_line in wrapped_answer_lines:
                if first_visual_line:
                    rendered_answers.append(f"{prefix}{wrapped_line}")
                    first_visual_line = False
                else:
                    rendered_answers.append(wrapped_line)

    lines = [
        "Adaptive Learning Demo",
        f"Question {question_number} of {total_questions}",
        "",
        *question_lines,
        "",
        *rendered_answers,
        "",
        HELP_TEXT,
    ]
    return "\n".join(lines) + "\n"


def _replace_stream_contents(stream: object) -> bool:
    seek = getattr(stream, "seek", None)
    truncate = getattr(stream, "truncate", None)
    if callable(seek) and callable(truncate):
        try:
            seek(0)
            truncate(0)
            return True
        except Exception:
            pass

    parts = getattr(stream, "parts", None)
    if isinstance(parts, list):
        parts.clear()
        return True

    return False


def draw_frame(stdout: object, frame: str) -> None:
    is_tty = bool(getattr(stdout, "isatty", lambda: False)())
    previous_length = int(getattr(stdout, "_adaptive_learning_previous_frame_length", 0) or 0)

    if is_tty:
        stdout.write(CLEAR_SCREEN)
        stdout.write(frame)
    else:
        if previous_length:
            _replace_stream_contents(stdout)
        stdout.write(" " * previous_length)
        stdout.write(CLEAR_SCREEN)
        stdout.write(frame)

    stdout.flush()
    setattr(stdout, "_adaptive_learning_previous_frame_length", len(CLEAR_SCREEN) + len(frame))


def read_key(stdin: object) -> Command:
    if os.name == "nt":
        key = msvcrt.getwch()
        if key in ("\r", "\n"):
            return "submit"
        if key.lower() == "q":
            return "quit"
        if key in ("\x00", "\xe0"):
            key = msvcrt.getwch()
            if key == "H":
                return "up"
            if key == "P":
                return "down"
        if key.lower() == "k":
            return "up"
        if key.lower() == "j":
            return "down"
        return "noop"

    key = stdin.read(1)
    if key in ("\r", "\n"):
        return "submit"
    if key.lower() == "q":
        return "quit"
    if key.lower() == "k":
        return "up"
    if key.lower() == "j":
        return "down"
    if key == "\x1b":
        next_key = stdin.read(1)
        if next_key != "[":
            return "noop"
        arrow = stdin.read(1)
        if arrow == "A":
            return "up"
        if arrow == "B":
            return "down"
    return "noop"


class TerminalView:
    def __init__(self, *, stdin: object | None = None, stdout: object | None = None) -> None:
        self.stdin = sys.stdin if stdin is None else stdin
        self.stdout = sys.stdout if stdout is None else stdout
        self._raw_terminal: RawTerminal | None = None

    def __enter__(self) -> "TerminalView":
        ensure_interactive_terminal(self.stdin, self.stdout)
        self._raw_terminal = RawTerminal(self.stdin)
        self._raw_terminal.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._raw_terminal is not None:
            self._raw_terminal.__exit__(exc_type, exc_value, traceback)
            self._raw_terminal = None

    def clear_screen(self) -> None:
        self.stdout.write(CLEAR_SCREEN)
        self.stdout.flush()

    def read_command(self) -> Command:
        return read_key(self.stdin)

    def render_question(self, state: QuizState, question_number: int, total_questions: int) -> None:
        draw_frame(
            self.stdout,
            render_screen(
                question=state.question.prompt,
                answers=state.question.answers,
                selected_index=state.selected_index,
                question_number=question_number,
                total_questions=total_questions,
            ),
        )

    def render_feedback(self, state: QuizState) -> None:
        self.stdout.write("\n")
        if state.is_correct():
            self.stdout.write("Correct.\n")
        else:
            correct_answer = state.question.answers[state.question.correct_answer]
            self.stdout.write(f"Incorrect. Correct answer: {correct_answer}\n")
        self.stdout.write("Press Enter to continue.\n")
        self.stdout.flush()

    def wait_for_submit_or_quit(self) -> bool:
        while True:
            command = self.read_command()
            if command == "quit":
                return False
            if command == "submit":
                return True

    def show_early_exit(self, score: int, total_questions: int) -> None:
        self.stdout.write(f"Quiz ended early. Score: {score}/{total_questions}\n")
        self.stdout.flush()

    def show_final_score(self, score: int, total_questions: int) -> None:
        self.stdout.write(f"Final score: {score}/{total_questions}\n")
        self.stdout.flush()
