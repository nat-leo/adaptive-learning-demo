from __future__ import annotations

from pathlib import Path

import pytest

import adaptive_learning.cli as cli
from adaptive_learning.models import Question, QuizState


def _sample_question() -> Question:
    return Question(
        id="q-cli",
        prompt="Prompt",
        answers=["A", "B"],
        correct_answer="A",
        rating=10,
    )


def test_problem_files_returns_sorted_json_paths() -> None:
    files = cli.problem_files()

    assert files
    assert files == sorted(files)
    assert all(path.suffix == ".json" for path in files)


def test_run_quiz_wires_problem_files_loader_controller_and_view(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    fake_paths = [Path("easy.json"), Path("hard.json")]
    fake_questions = [_sample_question()]

    monkeypatch.setattr(cli, "problem_files", lambda: fake_paths)

    def fake_load_from_many(paths: list[Path]) -> list[Question]:
        observed["paths"] = paths
        return fake_questions

    class FakeTerminalView:
        pass

    class FakeController:
        def __init__(self, *, questions: list[Question], view: object) -> None:
            observed["questions"] = questions
            observed["view"] = view

        def run(self) -> int:
            return 7

    monkeypatch.setattr(cli.data, "load_from_many", fake_load_from_many)
    monkeypatch.setattr(cli, "TerminalView", FakeTerminalView)
    monkeypatch.setattr(cli, "QuizController", FakeController)

    code = cli.run_quiz()

    assert code == 7
    assert observed["paths"] == fake_paths
    assert observed["questions"] == fake_questions
    assert isinstance(observed["view"], FakeTerminalView)


@pytest.mark.parametrize(
    "exception,stderr_fragment",
    [
        (FileNotFoundError("missing.json"), "missing.json"),
        (ValueError("bad json"), "Invalid question file: bad json"),
        (RuntimeError("tty missing"), "tty missing"),
    ],
)
def test_main_maps_known_runtime_failures_to_exit_code_2(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    exception: Exception,
    stderr_fragment: str,
) -> None:
    def raise_error() -> int:
        raise exception

    monkeypatch.setattr(cli, "run_quiz", raise_error)

    code = cli.main()
    captured = capsys.readouterr()

    assert code == 2
    assert stderr_fragment in captured.err


def test_main_returns_run_quiz_exit_code_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "run_quiz", lambda: 0)
    assert cli.main() == 0


def test_wrapper_functions_delegate_to_underlying_view_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    class FakeTerminalView:
        def clear_screen(self) -> None:
            observed["clear_screen"] = True

        def render_feedback(self, state: QuizState) -> None:
            observed["render_feedback_state"] = state

    monkeypatch.setattr(cli, "TerminalView", FakeTerminalView)
    monkeypatch.setattr(cli, "_ensure_interactive_terminal", lambda stdin, stdout: observed.setdefault("ensure", (stdin, stdout)))
    monkeypatch.setattr(cli, "_render_screen", lambda **kwargs: "FRAME")
    monkeypatch.setattr(cli, "_draw_frame", lambda stdout, frame: observed.setdefault("draw", (stdout, frame)))
    monkeypatch.setattr(cli, "_read_key", lambda stdin: "noop")

    state = QuizState(question=_sample_question())

    cli.clear_screen()
    cli.ensure_interactive_terminal()
    assert cli.render_screen("Q", ["A", "B"], 0, question_number=1, total_questions=2) == "FRAME"
    cli.draw_frame("stream", "frame")
    assert cli.read_key() == "noop"
    cli.render_feedback(state)

    assert observed["clear_screen"] is True
    assert observed["draw"] == ("stream", "frame")
    assert observed["render_feedback_state"] is state
    assert observed["ensure"][0] is cli.sys.stdin
    assert observed["ensure"][1] is cli.sys.stdout


def test_render_question_wrapper_documents_current_keyword_mismatch_bug() -> None:
    state = QuizState(question=_sample_question())

    with pytest.raises(TypeError, match="question_number"):
        cli.render_question(state, question_number=1, total_questions=1)
