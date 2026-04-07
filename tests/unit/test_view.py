from __future__ import annotations

import io
from datetime import datetime

import pytest

import adaptive_learning.view as view
from adaptive_learning.models import IncorrectQuestion, Question, QuizState, SessionData


class _FakeStdout:
    def __init__(self, *, tty: bool) -> None:
        self._tty = tty
        self.parts: list[str] = []

    def isatty(self) -> bool:
        return self._tty

    def write(self, text: str) -> int:
        self.parts.append(text)
        return len(text)

    def flush(self) -> None:
        pass

    def getvalue(self) -> str:
        return "".join(self.parts)


@pytest.mark.parametrize(
    "stdin_tty,stdout_tty,should_raise",
    [
        (True, True, False),
        (False, True, True),
        (True, False, True),
    ],
)
def test_ensure_interactive_terminal_contract(stdin_tty: bool, stdout_tty: bool, should_raise: bool) -> None:
    class _S:
        def __init__(self, flag: bool) -> None:
            self._flag = flag

        def isatty(self) -> bool:
            return self._flag

    stdin = _S(stdin_tty)
    stdout = _S(stdout_tty)

    if should_raise:
        with pytest.raises(RuntimeError, match="interactive terminal"):
            view.ensure_interactive_terminal(stdin, stdout)
    else:
        view.ensure_interactive_terminal(stdin, stdout)


def test_render_screen_wraps_content_and_marks_selected_answer() -> None:
    screen = view.render_screen(
        question="Which layer of TCP/IP routes packets between networks?",
        answers=["Application layer", "Internet layer", "Link layer"],
        selected_index=1,
        number_correct=3,
        total_questions=9,
    )

    assert "Adaptive Learning Demo" in screen
    assert "Question 3 of 9" in screen
    assert "> Internet layer" in screen
    assert "Use ↑/↓ or j/k to move, Enter to submit, q to quit." in screen


def test_render_session_summary_includes_accuracy_and_lifetime_line() -> None:
    session = SessionData(
        session_id="s-1",
        started_at=datetime(2026, 4, 1, 12, 0, 0),
        questions_seen=4,
        questions_correct=3,
    )

    summary = view.render_session_summary(session, total_score=10, total_attempts=20)

    assert "Session Summary" in summary
    assert "Session Accuracy: 75.0%" in summary
    assert "Lifetime Score: 10/20" in summary


def test_render_incorrect_questions_summary_handles_empty_and_populated_states() -> None:
    empty = view.render_incorrect_questions_summary({})
    assert empty == "Incorrect Questions\n<none>\n"

    populated = view.render_incorrect_questions_summary(
        {
            "q1": IncorrectQuestion(
                question_id="q1",
                category="easy",
                times_wrong=2,
                times_seen_since_wrong=1,
                reintroduction_streak=1,
                due_in=0,
                last_seen=0,
            )
        }
    )

    assert "- q1: category=easy" in populated
    assert "due_in=None" in populated
    assert "last_seen=None" in populated


def test_replace_stream_contents_supports_seek_truncate_and_parts_lists() -> None:
    buffer = io.StringIO("abc")
    assert view._replace_stream_contents(buffer) is True
    assert buffer.getvalue() == ""

    class WithParts:
        def __init__(self) -> None:
            self.parts = ["a", "b"]

    parts_stream = WithParts()
    assert view._replace_stream_contents(parts_stream) is True
    assert parts_stream.parts == []

    class Unsupported:
        pass

    assert view._replace_stream_contents(Unsupported()) is False


def test_draw_frame_replaces_previous_content_for_non_tty_streams() -> None:
    out = _FakeStdout(tty=False)

    first = view.render_screen(
        question="Question one?",
        answers=["A", "B"],
        selected_index=0,
        number_correct=1,
        total_questions=2,
    )
    second = view.render_screen(
        question="Question two?",
        answers=["C", "D"],
        selected_index=1,
        number_correct=2,
        total_questions=2,
    )

    view.draw_frame(out, first)
    first_snapshot = out.getvalue()

    view.draw_frame(out, second)
    second_snapshot = out.getvalue()

    assert first_snapshot != second_snapshot
    assert view.CLEAR_SCREEN in second_snapshot
    assert "Question one?" not in second_snapshot
    assert "Question two?" in second_snapshot


def test_draw_frame_writes_clear_sequence_for_tty_streams() -> None:
    out = _FakeStdout(tty=True)
    frame = view.render_screen(
        question="TTY question?",
        answers=["Yes", "No"],
        selected_index=0,
    )

    view.draw_frame(out, frame)
    combined = out.getvalue()

    assert combined.startswith(view.CLEAR_SCREEN)
    assert "TTY question?" in combined


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("\n", "submit"),
        ("q", "quit"),
        ("k", "up"),
        ("j", "down"),
        ("\x1b[A", "up"),
        ("\x1b[B", "down"),
        ("x", "noop"),
        ("\x1bX", "noop"),
    ],
)
def test_read_key_posix_mappings(raw: str, expected: str) -> None:
    assert view.read_key(io.StringIO(raw)) == expected


def test_terminal_view_methods_cover_feedback_wait_and_summary_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    entered: list[bool] = []
    exited: list[bool] = []

    class DummyRaw:
        def __init__(self, stdin: object) -> None:
            self.stdin = stdin

        def __enter__(self) -> "DummyRaw":
            entered.append(True)
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            exited.append(True)

    monkeypatch.setattr(view, "RawTerminal", DummyRaw)
    monkeypatch.setattr(view, "ensure_interactive_terminal", lambda stdin, stdout: None)

    stdout = _FakeStdout(tty=False)
    terminal = view.TerminalView(stdin=io.StringIO(""), stdout=stdout)

    question = Question(
        id="q-tv",
        prompt="Prompt",
        answers=["A", "B"],
        correct_answer="A",
        rating=10,
    )
    state = QuizState(question=question, selected_index=0)

    with terminal:
        terminal.clear_screen()
        terminal.render_question(state, number_correct=1, total_questions=3)
        terminal.render_feedback(state)

        commands = iter(["noop", "submit"])
        terminal.read_command = lambda: next(commands)
        assert terminal.wait_for_submit_or_quit() is True

        commands = iter(["noop", "quit"])
        terminal.read_command = lambda: next(commands)
        assert terminal.wait_for_submit_or_quit() is False

        session = SessionData(session_id="s", started_at=datetime(2026, 4, 1), questions_seen=1, questions_correct=1)
        terminal.show_session(session, total_score=1, total_attempts=1)
        terminal.show_incorrect_questions({})
        terminal.show_early_exit(1, 1)
        terminal.show_final_score(1, 1)

    written = stdout.getvalue()
    assert entered and exited
    assert "Correct." in written
    assert "Final score: 1/1" in written
