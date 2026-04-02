from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .data import load_questions
from .quiz import Command, QuizState, apply_command

if os.name == "nt":
    import msvcrt
else:
    import termios
    import tty


class RawTerminal:
    def __enter__(self) -> "RawTerminal":
        if os.name != "nt":
            self._fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(self._fd)
            tty.setraw(self._fd)
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
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def ensure_interactive_terminal() -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError("adaptive-learning requires an interactive terminal.")


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
    clear_screen()
    print("Adaptive Learning Demo")
    print(f"Question {question_number} of {total_questions}")
    print()
    print(state.question.prompt)
    print()

    for index, option in enumerate(state.question.options):
        marker = ">" if index == state.selected_index else " "
        print(f"{marker} {option}")

    print()
    print("Use ↑/↓ or j/k to move, Enter to submit, q to quit.")


def render_feedback(state: QuizState) -> None:
    print()
    if state.is_correct():
        print("Correct.")
    else:
        correct_answer = state.question.options[state.question.answer_index]
        print(f"Incorrect. Correct answer: {correct_answer}")
    print("Press Enter to continue.")


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
                    print(f"Quiz ended early. Score: {score}/{len(questions)}")
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
                print(f"Quiz ended early. Score: {score}/{len(questions)}")
                return 1

    clear_screen()
    print(f"Final score: {score}/{len(questions)}")
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
