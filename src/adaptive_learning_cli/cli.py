from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

if __package__ in {None, ""}:
    SRC_ROOT = Path(__file__).resolve().parents[1]
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))

    from adaptive_learning_cli.data import load_questions
    from adaptive_learning_cli.quiz import Command, QuizState, apply_command
else:
    from .data import load_questions
    from .quiz import Command, QuizState, apply_command

if os.name == "nt":
    import msvcrt
else:
    import termios
    import tty

CLEAR_SCREEN = "\033[H\033[2J\033[3J"
HELP_TEXT = "Use ↑/↓ or j/k to move, Enter to submit, q to quit."


class RawTerminal:
    def __enter__(self) -> "RawTerminal":
        if os.name != "nt":
            self._fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(self._fd)
            # cbreak keeps character-at-a-time input without disabling
            # output newline processing (raw mode causes visual line drift).
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if os.name != "nt":
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adaptive-learning",
        description="Practice multiple-choice questions in the terminal.",
    )
    parser.add_argument(
        "question_file",
        nargs="?",
        default="practice.json",
        help="Path to a JSON file containing quiz questions.",
    )
    return parser


def clear_screen() -> None:
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.flush()


def ensure_interactive_terminal() -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
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


def read_key() -> Command:
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

    key = sys.stdin.read(1)
    if key in ("\r", "\n"):
        return "submit"
    if key.lower() == "q":
        return "quit"
    if key.lower() == "k":
        return "up"
    if key.lower() == "j":
        return "down"
    if key == "\x1b":
        next_key = sys.stdin.read(1)
        if next_key != "[":
            return "noop"
        arrow = sys.stdin.read(1)
        if arrow == "A":
            return "up"
        if arrow == "B":
            return "down"
    return "noop"


def render_question(state: QuizState, question_number: int, total_questions: int) -> None:
    draw_frame(
        sys.stdout,
        render_screen(
            question=state.question.prompt,
            answers=state.question.options,
            selected_index=state.selected_index,
            question_number=question_number,
            total_questions=total_questions,
        )
    )


def render_feedback(state: QuizState) -> None:
    print(end="\n")
    if state.is_correct():
        print("Correct.", end="\n")
    else:
        correct_answer = state.question.options[state.question.answer_index]
        print(f"Incorrect. Correct answer: {correct_answer}", end="\n")
    print("Press Enter to continue.", end="\n")


def wait_for_enter() -> bool:
    while True:
        command = read_key()
        if command == "quit":
            return False
        if command == "submit":
            return True


def run_quiz(question_file: Path) -> int:
    ensure_interactive_terminal()
    questions = load_questions(question_file)
    score = 0

    with RawTerminal():
        for number, question in enumerate(questions, start=1):
            state = QuizState(question=question)

            while True:
                render_question(state, question_number=number, total_questions=len(questions))
                command = read_key()

                if command == "quit":
                    clear_screen()
                    print(f"Quiz ended early. Score: {score}/{len(questions)}", end="\n")
                    return 1

                if command == "submit":
                    break

                apply_command(state, command)

            if state.is_correct():
                score += 1

            render_question(state, question_number=number, total_questions=len(questions))
            render_feedback(state)
            if not wait_for_enter():
                clear_screen()
                print(f"Quiz ended early. Score: {score}/{len(questions)}", end="\n")
                return 1

    clear_screen()
    print(f"Final score: {score}/{len(questions)}", end="\n")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return run_quiz(Path(args.question_file))
    except FileNotFoundError as error:
        parser.exit(status=2, message=f"{error}\n")
    except ValueError as error:
        parser.exit(status=2, message=f"Invalid question file: {error}\n")
    except RuntimeError as error:
        parser.exit(status=2, message=f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
