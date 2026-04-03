from __future__ import annotations

import os
import pty
import re
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

if os.name != "nt":
    import fcntl
    import struct
    import termios


CLEAR_SCREEN = "\x1b[H\x1b[2J\x1b[3J"
EXPECTED_INITIAL_SCREEN = """Adaptive Learning Demo\nQuestion 1 of 60\n\nWhich layer of the TCP/IP model is responsible for routing\npackets between networks?\n\n> Application layer\nInternet layer\nLink layer\n\nUse ↑/↓ or j/k to move, Enter to submit, q to quit."""


def _read_until(master_fd: int, pattern: str, timeout: float = 3.0) -> str:
    deadline = time.monotonic() + timeout
    chunks: list[str] = []

    while time.monotonic() < deadline:
        ready, _, _ = select.select([master_fd], [], [], 0.05)
        if master_fd not in ready:
            continue

        chunk = os.read(master_fd, 4096)
        if not chunk:
            break

        chunks.append(chunk.decode("utf-8", errors="ignore"))
        transcript = "".join(chunks)
        if pattern in transcript:
            return transcript

    raise AssertionError(f"Timed out waiting for CLI output containing: {pattern!r}")


def strip_ansi(text: str) -> str:
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", text)


def _set_terminal_size(fd: int, width: int, height: int) -> None:
    if os.name == "nt":
        return

    winsize = struct.pack("HHHH", height, width, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def _fixed_terminal_size() -> os.terminal_size:
    return os.terminal_size((80, 24))


def test_running_cli_script_starts_cli() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cli_path = repo_root / "src" / "adaptive_learning_cli" / "cli.py"

    result = subprocess.run(
        [sys.executable, str(cli_path)],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode == 2
    assert "adaptive-learning requires an interactive terminal." in result.stderr
    assert "ImportError" not in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="PTY interaction test requires POSIX terminals.")
def test_adaptive_learning_initial_screen_matches_expected_output() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cli_path = repo_root / "src" / "adaptive_learning_cli" / "cli.py"
    master_fd, slave_fd = pty.openpty()
    _set_terminal_size(slave_fd, width=120, height=24)

    process = subprocess.Popen(
        [sys.executable, str(cli_path)],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=repo_root,
        close_fds=True,
    )
    os.close(slave_fd)

    try:
        transcript = _read_until(master_fd, "Use ↑/↓ or j/k to move, Enter to submit, q to quit.")
        os.write(master_fd, b"q")

        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and process.poll() is None:
            ready, _, _ = select.select([master_fd], [], [], 0.05)
            if master_fd in ready:
                chunk = os.read(master_fd, 4096)
                if not chunk:
                    break
            else:
                continue
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)
        os.close(master_fd)

    frames = transcript.split(CLEAR_SCREEN)
    assert len(frames) >= 2
    initial_screen = frames[1].replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    assert initial_screen == EXPECTED_INITIAL_SCREEN


def test_question_render_does_not_soft_wrap_or_overflow() -> None:
    from adaptive_learning_cli.cli import render_screen

    width = 80

    question = (
        "Which layer of the TCP/IP model is responsible for routing "
        "packets between networks?"
    )
    answers = [
        "Application layer",
        "Internet layer",
        "Link layer",
    ]

    screen = render_screen(
        question=question,
        answers=answers,
        selected_index=0,
    )

    screen = strip_ansi(screen)
    lines = screen.splitlines()

    too_wide = [line for line in lines if len(line) > width]
    assert not too_wide, (
        "Rendered output contains line(s) wider than terminal width. "
        "That causes terminal soft-wrap and broken layout.\n\n"
        + "\n".join(repr(line) for line in too_wide)
    )

    question_fragments = [
        "Which layer of the TCP/IP model is responsible for routing",
        "packets between networks?",
    ]

    for fragment in question_fragments:
        assert any(fragment in line for line in lines), (
            f"Expected wrapped question fragment not found: {fragment!r}\n\n"
            f"Rendered output:\n{screen}"
        )

    for answer in answers:
        matches = [line for line in lines if answer in line]
        assert matches, f"Answer {answer!r} not found in output.\n\n{screen}"
        assert len(matches) == 1, (
            f"Answer {answer!r} appeared multiple times unexpectedly.\n\n{screen}"
        )


def test_question_lines_are_wrapped_before_centering() -> None:
    from adaptive_learning_cli.cli import render_screen

    question = (
        "Which layer of the TCP/IP model is responsible for routing "
        "packets between networks?"
    )

    screen = render_screen(
        question=question,
        answers=["Application layer", "Internet layer", "Link layer"],
        selected_index=0,
    )

    screen = strip_ansi(screen)
    lines = screen.splitlines()

    question_lines = [
        line
        for line in lines
        if "Which layer of the TCP/IP model" in line
        or "packets between networks?" in line
    ]

    assert len(question_lines) >= 2, (
        "Question was not explicitly wrapped onto multiple rendered lines.\n\n"
        "It is likely being centered as one long string and depending on "
        "terminal soft-wrap.\n\n"
        f"{screen}"
    )

def test_ui_renders_newline_joined_text_not_python_list_repr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from adaptive_learning_cli.cli import render_screen

    sys.stdout.write(
        render_screen(
            question=(
                "Which layer of the TCP/IP model is responsible for routing "
                "packets between networks?"
            ),
            answers=[
                "Application layer",
                "Internet layer",
                "Link layer",
            ],
            selected_index=0,
            question_number=1,
            total_questions=22,
        )
    )

    out = capsys.readouterr().out

    expected = "Adaptive Learning Demo\nQuestion 1 of 22\n\nWhich layer of the TCP/IP model is responsible for routing\npackets between networks?\n\n> Application layer\nInternet layer\nLink layer\n\nUse ↑/↓ or j/k to move, Enter to submit, q to quit.\n"

    assert out == expected


def test_answers_are_left_aligned_as_a_block() -> None:
    from adaptive_learning_cli.cli import render_screen

    output = render_screen(
        question="Pick the correct option.",
        answers=[
            "Application layer\nInternet layer",
            "Internet layer",
            "Link layer",
        ],
        selected_index=0,
        question_number=1,
        total_questions=22,
    )

    lines = output.splitlines()

    selected_line_index = next(
        (index for index, line in enumerate(lines) if line.startswith("> ")),
        None,
    )
    assert selected_line_index is not None, f"Selected answer line not found.\n\n{output}"

    assert lines[selected_line_index] == "> Application layer"
    assert lines[selected_line_index + 1] == "Internet layer"
    assert lines[selected_line_index + 1] == lines[selected_line_index + 1].lstrip(" "), (
        "Text intended for the next line has unexpected left padding."
    )


def test_redraw_replaces_screen_instead_of_appending_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Catches the bug where each new UI frame is printed below the previous one
    instead of replacing the old screen contents.
    """
    from adaptive_learning_cli import cli
    from adaptive_learning_cli.models import Question
    from adaptive_learning_cli.quiz import QuizState

    class FakeStdout:
        def __init__(self) -> None:
            self.parts: list[str] = []

        def write(self, s: str) -> int:
            self.parts.append(s)
            return len(s)

        def flush(self) -> None:
            pass

        def getvalue(self) -> str:
            return "".join(self.parts)

    out = FakeStdout()
    monkeypatch.setattr(cli.sys, "stdout", out)
    state_one = QuizState(
        question=Question(
            prompt="Which layer routes packets between networks?",
            answers=["Application layer", "Internet layer", "Link layer"],
            correct_answer=1,
        ),
        selected_index=0,
    )
    state_two = QuizState(
        question=Question(
            prompt="Which protocol is connectionless?",
            answers=["TCP", "UDP", "ARP"],
            correct_answer=1,
        ),
        selected_index=1,
    )

    cli.render_question(state_one, question_number=1, total_questions=22)
    first = out.getvalue()

    cli.render_question(state_two, question_number=2, total_questions=22)
    second = out.getvalue()

    appended_suffix = second[len(first):]

    has_redraw_control = any(
        token in appended_suffix
        for token in [
            "\x1b[H",
            "\x1b[2J",
            "\x1b[3J",
            "\x1b[1;1H",
            "\r",
        ]
    )

    assert has_redraw_control, (
        "Second frame appears to be appended to stdout without any redraw control.\n\n"
        "Expected ANSI clear/home or similar cursor reset before drawing the new frame.\n\n"
        f"First output:\n{first!r}\n\n"
        f"Appended suffix:\n{appended_suffix!r}"
    )

    plain = strip_ansi(second)
    assert not ("Question 1 of 22" in plain and "Question 2 of 22" in plain), (
        "Output contains both old and new frame headers in the final stream, "
        "which strongly suggests frame appending instead of replacement.\n\n"
        f"{plain}"
    )


def test_multiple_redraws_do_not_duplicate_static_ui_text(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Lightweight stdout-only version.

    If the program redraws by plain print() appends, repeated static strings like
    help text will accumulate multiple times in captured stdout.
    """
    from adaptive_learning_cli import cli
    from adaptive_learning_cli.models import Question
    from adaptive_learning_cli.quiz import QuizState

    cli.render_question(
        QuizState(
            question=Question(
                prompt="Which layer routes packets between networks?",
                answers=["Application layer", "Internet layer", "Link layer"],
                correct_answer=1,
            ),
            selected_index=0,
        ),
        question_number=1,
        total_questions=22,
    )
    cli.render_question(
        QuizState(
            question=Question(
                prompt="Which protocol is connectionless?",
                answers=["TCP", "UDP", "ARP"],
                correct_answer=1,
            ),
            selected_index=1,
        ),
        question_number=2,
        total_questions=22,
    )

    captured = capsys.readouterr().out
    plain = strip_ansi(captured)

    help_text = "Use ↑/↓ or j/k to move, Enter to submit, q to quit."
    count = plain.count(help_text)
    assert count <= 1, (
        "Static UI text was printed multiple times across redraws, which suggests "
        "new frames are being appended instead of replacing the previous frame.\n\n"
        f"Count for {help_text!r}: {count}\n\n"
        f"Captured stdout:\n{plain}"
    )


def test_final_visible_frame_contains_only_latest_question() -> None:
    """
    Best test if you have a pure renderer + a terminal buffer abstraction.

    It catches the case where the old question remains visible after advancing.
    """
    from adaptive_learning_cli.cli import render_screen

    class TerminalBuffer:
        def __init__(self, width: int, height: int) -> None:
            self.width = width
            self.height = height
            self._visible = ""

        def draw(self, frame: str) -> None:
            self._visible = frame

        def render(self) -> str:
            return self._visible

    def render_into_buffer(
        buf: TerminalBuffer,
        *,
        question: str,
        answers: list[str],
        selected_index: int,
        question_number: int,
        total_questions: int,
    ) -> None:
        buf.draw(
            render_screen(
                question=question,
                answers=answers,
                selected_index=selected_index,
                question_number=question_number,
                total_questions=total_questions,
            )
        )

    buf = TerminalBuffer(width=80, height=24)

    render_into_buffer(
        buf,
        question="Which layer routes packets between networks?",
        answers=["Application layer", "Internet layer", "Link layer"],
        selected_index=0,
        question_number=1,
        total_questions=22,
    )
    render_into_buffer(
        buf,
        question="Which protocol is connectionless?",
        answers=["TCP", "UDP", "ARP"],
        selected_index=1,
        question_number=2,
        total_questions=22,
    )

    visible = strip_ansi(buf.render())

    assert "Question 2 of 22" in visible, f"Latest frame header missing.\n\n{visible}"
    assert "Question 1 of 22" not in visible, (
        "Old frame header is still visible after redraw. "
        "That means the new UI did not fully replace the old UI.\n\n"
        f"{visible}"
    )
