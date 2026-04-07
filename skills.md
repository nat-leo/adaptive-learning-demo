# Pytest Skills: Testing Python Systems and Antagonistically Breaking CLI Tools

This guide teaches practical `pytest` for real projects, with a heavy emphasis on **breaking CLI applications on purpose**.

It is written for people who do not just want passing tests. It is written for people who want tests that catch the kinds of bugs users actually trigger.

---

## 1. What this file is for

This file has three goals:

1. Teach the core mechanics of `pytest`
2. Give you a framework for **antagonistic testing** of CLI tools
3. Show how testing strategy changes in **MVC-style projects**

The center of gravity is **CLI testing**, especially hostile, adversarial, edge-case-heavy testing.

---

## 2. The mental model of pytest

`pytest` is a test runner that makes it easy to:

- write small tests as plain functions
- use `assert` directly
- share setup through fixtures
- parametrize many cases cleanly
- organize tests by behavior instead of by class hierarchy

A minimal test looks like this:

```python
def add(a, b):
    return a + b


def test_add():
    assert add(2, 3) == 5
```

Run it with:

```bash
pytest
```

Run a specific file:

```bash
pytest tests/test_math.py
```

Run a specific test:

```bash
pytest tests/test_math.py -k test_add
```

Show print output:

```bash
pytest -s
```

Stop on first failure:

```bash
pytest -x
```

---

## 3. Recommended project layout

```text
project/
├─ src/
│  └─ myapp/
│     ├─ cli.py
│     ├─ controller.py
│     ├─ service.py
│     ├─ models.py
│     └─ view.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ e2e/
│  ├─ conftest.py
│  └─ helpers.py
├─ pyproject.toml
└─ README.md
```

A useful split is:

- `tests/unit/`: fast tests of isolated logic
- `tests/integration/`: boundaries between modules, file system, subprocesses, DB, APIs
- `tests/e2e/`: run the full CLI the way a user would

---

## 4. Pytest basics you actually need

### 4.1 Assertions

Use plain `assert`.

```python
def test_total():
    result = 2 + 2
    assert result == 4
```

Pytest gives better failure output than `unittest`-style assertion methods.

### 4.2 Exceptions

```python
import pytest


def parse_age(value: str) -> int:
    age = int(value)
    if age < 0:
        raise ValueError("age must be non-negative")
    return age


def test_parse_age_rejects_negative():
    with pytest.raises(ValueError, match="non-negative"):
        parse_age("-1")
```

### 4.3 Parametrization

This is critical for CLI testing.

```python
import pytest


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1", 1),
        (" 42 ", 42),
        ("0007", 7),
    ],
)
def test_parse_int_valid(raw, expected):
    assert int(raw) == expected
```

You should parametrize:

- normal inputs
- boundaries
- malformed input
- hostile input
- weird formatting

### 4.4 Fixtures

Fixtures create reusable setup.

```python
import pytest
from pathlib import Path


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    path.write_text('{"debug": true}')
    return path


def test_reads_config(temp_config):
    assert temp_config.read_text() == '{"debug": true}'
```

### 4.5 Monkeypatch

Use `monkeypatch` to replace environment variables, functions, input streams, or global state.

```python
def test_reads_env(monkeypatch):
    monkeypatch.setenv("APP_MODE", "test")
    assert __import__("os").environ["APP_MODE"] == "test"
```

### 4.6 Capturing stdout and stderr

Very important for CLIs.

```python
def greet():
    print("hello")


def test_greet(capsys):
    greet()
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
    assert captured.err == ""
```

### 4.7 Temp directories

Use `tmp_path` for files.

```python
def test_writes_output(tmp_path):
    out = tmp_path / "result.txt"
    out.write_text("ok")
    assert out.read_text() == "ok"
```

---

## 5. The testing pyramid for CLI tools

For CLI-heavy applications, a practical pyramid is:

### Unit tests
Focus on pure logic.

Examples:

- arg parsing helpers
- validators
- formatting logic
- routing logic
- state transitions
- model rules

### Integration tests
Focus on real boundaries.

Examples:

- controller calling service layer
- file reads and writes
- environment variables
- subprocess invocation
- DB or network mocking at the process boundary

### End-to-end tests
Focus on the actual user journey.

Examples:

- invoking the CLI as a subprocess
- entering input
- getting output
- checking exit codes
- checking file system side effects

### Where the main focus is

For a CLI product, the **main emphasis should usually be**:

1. **Unit tests for decision logic and rendering logic**
2. **A smaller number of very high-value end-to-end tests**
3. Integration tests where there is meaningful complexity at the boundaries

Why:

- unit tests are cheap, fast, and precise
- e2e tests catch wiring mistakes and user-visible failures
- too many e2e tests become slow and fragile

For an antagonistic CLI strategy, the best ROI often comes from:

- many hostile unit tests around parsing, routing, and rendering
- a curated set of e2e tests that simulate real abuse

---

## 6. Unit vs end-to-end testing for CLI tools

## Unit testing

Unit tests isolate a small behavior.

You test one thing at a time:

- does this parser reject bad flags?
- does this renderer format output correctly?
- does this validator reject empty input?
- does this controller choose the right action?

Unit tests should answer: **is the logic correct?**

Example:

```python
def normalize_name(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("name required")
    return cleaned


def test_normalize_name_strips_whitespace():
    assert normalize_name("  Nate  ") == "Nate"


def test_normalize_name_rejects_blank():
    import pytest
    with pytest.raises(ValueError):
        normalize_name("   ")
```

## End-to-end testing

E2E tests run the CLI the way a user does.

You test the whole path:

- shell command
- args
- env
- stdin
- stdout/stderr
- exit code
- filesystem effects

E2E tests should answer: **does the whole thing work when used for real?**

Example using `subprocess`:

```python
import subprocess
import sys


def test_cli_help_shows_usage():
    result = subprocess.run(
        [sys.executable, "-m", "myapp.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()
```

## The practical distinction

Unit tests are for:

- correctness
- branch coverage
- fast feedback
- edge cases

E2E tests are for:

- wiring
- real UX behavior
- regressions in argument parsing
- regressions in output rendering
- crashes caused by startup/config/environment

---

## 7. The core framework for antagonistic CLI testing

Antagonistic testing means you test the CLI the way a hostile, careless, confused, rushed, or inventive user would use it.

Not just:

- “does it work when used correctly?”

But:

- “how does it fail?”
- “does it fail safely?”
- “does it corrupt state?”
- “does it hang?”
- “does it render garbage?”
- “does it mislead the user?”

Use this framework.

### Category A: Input attacks

Test weird input values.

- empty string
- all whitespace
- extremely long strings
- unicode
- emoji
- escape sequences
- embedded null-like content where relevant
- malformed JSON
- malformed CSV
- invalid numbers
- negative numbers where impossible
- floats where ints are expected
- duplicate flags
- conflicting flags

### Category B: Interaction attacks

Test weird user behavior.

- pressing Enter immediately
- repeated Enter
- invalid menu selection then valid one
- quit in the middle of flow
- interrupt during prompt
- sending EOF
- piping no input
- extra trailing input
- terminal resize assumptions if applicable

### Category C: State attacks

Test corrupted or unexpected state.

- missing config file
- empty config file
- half-written config file
- invalid schema
- stale lock file
- output file already exists
- read-only destination
- missing environment variables
- mutually inconsistent sources of truth

### Category D: Environment attacks

Test hostile runtime conditions.

- non-interactive terminal
- weird working directory
- no permissions
- no HOME directory
- locale differences
- path with spaces
- path with unicode
- CRLF vs LF assumptions
- clock/timezone assumptions

### Category E: Rendering attacks

Test what the user sees.

- double-render bugs
- partial render bugs
- stale screen content
- ANSI escape leakage
- bad wrapping
- duplicated lines
- missing newline at end
- prompts printed to stderr by accident
- error text printed to stdout by accident

### Category F: Failure-path attacks

Test bad paths deliberately.

- dependency raises exception
- subprocess times out
- disk full simulation if abstracted
- parse failure midway through batch
- one item fails among many
- cleanup failure after success
- retry logic loops too long

### Category G: Security-ish CLI abuses

Depending on the tool, test:

- path traversal assumptions
- shell injection risks if building shell commands unsafely
- unsafe eval/exec behavior
- secrets accidentally printed in logs
- stack traces shown to users when they should be hidden
- credentials accepted via args and then leaked via process listings or logs

The goal is not maximal paranoia for its own sake. The goal is to make the CLI **predictable under abuse**.

---

## 8. Common hacks and abuse patterns against CLIs

These are common things users, testers, or attackers do that expose weak CLI design.

### 8.1 Smuggling whitespace

Examples:

- `"   "`
- tabs
- trailing spaces in filenames
- newline at the end of input

Test whether your tool trims, preserves, or rejects them intentionally.

### 8.2 Repeated flags and contradictory flags

Examples:

```bash
mytool --verbose --quiet
mytool --format json --format text
```

Test whether the behavior is documented and stable.

### 8.3 Giant inputs

Examples:

- huge pasted payloads
- giant file lists
- thousands of lines on stdin
- very long single-line input

Test for:

- hangs
- memory blowups
- truncated output
- unreadable errors

### 8.4 Malformed piped input

Examples:

```bash
echo '{bad json' | mytool
printf '' | mytool
```

The CLI should fail clearly and with the correct exit code.

### 8.5 ANSI and terminal control weirdness

If your CLI uses styling, test:

- output when color is disabled
- output when stdout is not a TTY
- raw escape codes appearing in logs or files

### 8.6 Path tricks

Examples:

- relative path vs absolute path
- `../` segments
- filenames starting with `-`
- spaces in names
- unicode filenames

### 8.7 Interrupted flows

Examples:

- Ctrl+C during prompt
- EOF during prompt
- partially written output if interrupted

### 8.8 Exit code manipulation

A broken CLI often prints an error but exits with code `0`.

Always test:

- successful path returns `0`
- usage errors return nonzero
- runtime failures return nonzero
- partial failures use a deliberate policy

### 8.9 Mixed stdout/stderr misuse

Common bug:

- machine-readable output goes to stdout
- human-readable errors should go to stderr

If your CLI emits JSON, do not pollute stdout with banners, progress text, or warnings.

### 8.10 Interactive rendering corruption

Common bug patterns:

- appending output instead of replacing the screen
- using blank list entries instead of actual newline behavior
- duplicated prompts after rerender
- cursor movement codes not cleared properly

These bugs deserve dedicated tests.

---

## 9. A practical rubric for antagonistic CLI test design

For any feature, ask these questions.

### Correctness

- Does it work on the happy path?
- Does it return the right value or output?

### Validation

- What invalid inputs exist?
- Are errors specific and useful?

### Boundary conditions

- Empty?
- One item?
- Very large?
- Maximum length?
- Minimum value?

### Rendering

- Is the output exact?
- Is the newline behavior correct?
- Does rerender replace instead of append?

### State safety

- What files or state are modified?
- What happens if the process dies midway?

### UX clarity

- Does the user know what happened?
- Is the error actionable?

### Operational safety

- Exit code correct?
- stderr/stdout split correct?
- Logs safe?

### Abuse resistance

- What would a careless or malicious user try?
- Does the program degrade gracefully?

---

## 10. CLI testing techniques in pytest

## 10.1 Test logic directly when possible

If your CLI has logic embedded in `main()`, refactor it.

Prefer:

```python
def run(args: list[str]) -> int:
    ...


def main() -> None:
    import sys
    raise SystemExit(run(sys.argv[1:]))
```

Then test `run()` as a unit and `main()` or `python -m ...` as e2e.

## 10.2 Capture output from in-process CLI runs

```python
def run(args):
    if "--help" in args:
        print("usage: mytool [OPTIONS]")
        return 0
    return 1


def test_run_help(capsys):
    code = run(["--help"])
    captured = capsys.readouterr()
    assert code == 0
    assert "usage:" in captured.out
```

## 10.3 Test subprocess behavior for true e2e

```python
import subprocess
import sys


def test_bad_flag_returns_nonzero():
    result = subprocess.run(
        [sys.executable, "-m", "myapp.cli", "--definitely-invalid"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert result.stderr or result.stdout
```

## 10.4 Simulate stdin

In-process:

```python
import io


def test_prompt_flow(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("hello\n"))
    name = input("Name: ")
    print(name)
    captured = capsys.readouterr()
    assert name == "hello"
    assert "Name:" in captured.out
```

Subprocess:

```python
import subprocess
import sys


def test_cli_accepts_piped_input():
    result = subprocess.run(
        [sys.executable, "-m", "myapp.cli"],
        input="hello\n",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
```

## 10.5 Test environment variables

```python
def test_requires_token(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    # call logic here and assert failure path
```

## 10.6 Test filesystem effects with tmp_path

```python
from pathlib import Path


def write_report(path: Path, text: str):
    path.write_text(text)


def test_write_report(tmp_path):
    target = tmp_path / "report.txt"
    write_report(target, "done")
    assert target.read_text() == "done"
```

---

## 11. Testing interactive CLI tools

Interactive CLIs are where many subtle bugs live.

Test these behaviors:

- initial render
- rerender after input
- selection movement
- invalid input recovery
- quit flow
- submit flow
- cursor positioning behavior if abstracted
- screen clearing behavior if abstracted

### Important design advice

Do not bury terminal behavior everywhere.

Abstract the terminal I/O behind small interfaces where possible.

Example:

```python
class Terminal:
    def write(self, text: str) -> None:
        ...

    def clear(self) -> None:
        ...
```

Then unit test rendering decisions without needing a real terminal.

### Example: catching append-vs-replace rendering bugs

If your renderer is supposed to fully redraw the screen, test that the second render does not contain stale content from the first render.

```python
class FakeTerminal:
    def __init__(self):
        self.writes = []

    def write(self, text: str):
        self.writes.append(text)


def render_screen(term, lines):
    term.write("\n".join(lines))


def test_render_replaces_full_screen_contract():
    term = FakeTerminal()
    render_screen(term, ["Title", "Question 1"])
    render_screen(term, ["Title", "Question 2"])

    assert term.writes[0] == "Title\nQuestion 1"
    assert term.writes[1] == "Title\nQuestion 2"
    assert "Question 1" not in term.writes[1]
```

If your real implementation is supposed to clear and rewrite the terminal, your abstraction should make that behavior testable directly.

---

## 12. MVC-style projects: what to test where

In an MVC-style Python project:

- **Model** = domain/data rules
- **View** = presentation/output formatting
- **Controller** = orchestration, routing, decision-making

For CLI systems, this maps cleanly.

### Model tests

Test:

- validation rules
- invariants
- transformations
- domain calculations
- serialization/deserialization if important

Example:

```python
from dataclasses import dataclass


@dataclass
class Account:
    balance: int

    def withdraw(self, amount: int):
        if amount <= 0:
            raise ValueError("amount must be positive")
        if amount > self.balance:
            raise ValueError("insufficient funds")
        self.balance -= amount


def test_withdraw_reduces_balance():
    acct = Account(balance=10)
    acct.withdraw(3)
    assert acct.balance == 7
```

### View tests

Test:

- exact text output
- JSON shape
- table layout
- newline behavior
- color/no-color modes
- deterministic formatting

Example:

```python
def render_error(message: str) -> str:
    return f"ERROR: {message}\n"


def test_render_error_exact_text():
    assert render_error("bad input") == "ERROR: bad input\n"
```

### Controller tests

Test:

- which service gets called
- how inputs are routed
- how failures are mapped to user-visible errors
- exit code decisions

Example:

```python
class FakeService:
    def __init__(self):
        self.called_with = None

    def create_user(self, name):
        self.called_with = name
        return {"ok": True}


def create_user_controller(service, raw_name: str) -> int:
    name = raw_name.strip()
    if not name:
        return 2
    service.create_user(name)
    return 0


def test_controller_strips_name_and_calls_service():
    svc = FakeService()
    code = create_user_controller(svc, "  Nate  ")
    assert code == 0
    assert svc.called_with == "Nate"
```

### Integration tests in MVC projects

These should test that:

- controller + model work together
- controller + view work together
- full command path preserves the intended contract

### Main point for MVC testing

Do not over-test the same behavior at every layer.

Instead:

- model tests prove rules
- view tests prove rendering
- controller tests prove orchestration
- e2e tests prove the user journey

---

## 13. Common test targets in MVC-style CLI apps

### Model-focused unit tests

- invalid state rejected
- derived fields correct
- sorting/filtering logic correct
- schema round-trips correctly

### View-focused unit tests

- exact prompt text
- exact error text
- exact spacing/newline behavior
- stable machine-readable output

### Controller-focused unit tests

- right branch taken for each command
- right service called
- right exit code returned
- expected failure translated correctly

### E2E tests

- `--help`
- valid command
- invalid command
- missing required arg
- interactive success flow
- interactive cancel flow
- file output flow
- nonzero exit on failure

---

## 14. Common failure modes to deliberately test in CLI projects

These are worth turning into a checklist.

### Parsing bugs

- accepts bad values silently
- rejects valid edge-case values
- conflicting flags not handled

### Rendering bugs

- duplicates lines
- broken spacing
- missing or extra newlines
- appends instead of rerenders
- status line not updated

### Error-handling bugs

- cryptic exception traceback
- failure message printed to stdout instead of stderr
- returns exit code 0 on failure

### State bugs

- overwrites existing file accidentally
- partial file written on error
- config migration corrupts data

### Environment bugs

- works only in one working directory
- fails with paths containing spaces
- assumes interactive terminal

### Testability bugs

- main logic trapped inside `if __name__ == "__main__":`
- hard-coded global state
- direct `print` everywhere with no abstraction in interactive apps
- direct `input()` calls spread throughout many layers

---

## 15. Example pytest patterns that scale well

## 15.1 Fixture for CLI runner helper

```python
import subprocess
import sys
import pytest


@pytest.fixture
def run_cli():
    def _run(*args, input_text=None, cwd=None, env=None):
        return subprocess.run(
            [sys.executable, "-m", "myapp.cli", *args],
            input=input_text,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
        )
    return _run
```

Usage:

```python
def test_help(run_cli):
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()
```

## 15.2 Parametrized hostile inputs

```python
import pytest


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "\t",
        "\n",
        "x" * 10000,
        "💥",
    ],
)
def test_name_validator_rejects_bad_values(raw):
    import pytest
    with pytest.raises(ValueError):
        validate_name(raw)
```

## 15.3 Golden-output testing for views

For stable text output, exact output snapshots can be useful.

```python
def test_render_summary():
    actual = render_summary(total=3, success=2, failed=1)
    expected = (
        "Summary\n"
        "-------\n"
        "Total: 3\n"
        "Success: 2\n"
        "Failed: 1\n"
    )
    assert actual == expected
```

Be careful: snapshot-like tests are useful for stable views, but can become noisy if overused.

---

## 16. What to mock and what not to mock

Mock external boundaries, not core logic.

Usually okay to mock:

- HTTP clients
- subprocess calls
- clock/time provider
- environment variables
- terminal abstraction
- file-reading abstraction in targeted unit tests

Usually avoid mocking:

- your own core business logic
- pure functions
- rendering functions unless you are testing a higher layer

Rule of thumb:

- unit test core logic directly
- mock expensive or nondeterministic boundaries
- run real subprocess/file/e2e tests for key user journeys

---

## 17. A suggested test plan for a CLI project

### Minimum viable unit coverage

- arg normalization
- validators
- controller routing
- error mapping
- output rendering
- exit code rules

### Minimum viable antagonistic coverage

- blank input
- malformed input
- giant input
- conflicting flags
- missing files
- output already exists
- interrupted or EOF input
- stdout/stderr split
- exact newline/render behavior

### Minimum viable e2e coverage

- help command
- one happy-path command
- one invalid-usage command
- one runtime failure command
- one interactive flow if interactive mode exists

---

## 18. How to decide where a bug should be tested

When you find a bug, ask:

1. What layer truly owns this behavior?
2. What is the cheapest test that would have caught it?
3. Do we also need one high-value e2e regression test?

Example:

- parser accepted invalid enum → unit test
- rerender appended old screen content → view/controller unit test, maybe one focused integration test
- packaged CLI crashes only when run as subprocess → e2e test

A good pattern is:

- add one precise low-level regression test
- add one e2e regression test only if the bug was about actual user execution wiring

---

## 19. Anti-patterns in pytest for CLI work

Avoid these.

### Over-relying on e2e tests

They are slower, noisier, and harder to debug.

### Mocking everything

Then you prove only that your mocks agree with your assumptions.

### Not checking exit codes

A CLI can print the right thing and still fail operationally.

### Testing vague output instead of exact output

For views and CLI rendering, exactness matters.

### Ignoring stderr

A lot of bugs hide there.

### Letting interactive terminal logic sprawl everywhere

This makes the CLI hard to test and easy to break.

### Treating “does not crash” as enough

A CLI can avoid crashing and still be wrong, misleading, or unusable.

---

## 20. A compact checklist for antagonistic CLI testing

For each command or screen, verify:

- happy path works
- bad input fails clearly
- blank input handled
- large input handled
- exit code correct
- stdout/stderr split correct
- exact output format correct
- files/state changes correct
- missing config/env handled
- interruption or EOF handled
- rerender behavior correct
- no stale content remains

---

## 21. Final principle

A CLI is a user interface.

That means correctness is not enough.

You need to test:

- logic
- rendering
- state transitions
- recovery from bad input
- behavior under abuse

The best CLI test suites are not polite. They are skeptical.

They assume the user will:

- mistype things
- paste garbage
- hit Enter too soon
- pipe malformed data
- run the command in the wrong directory
- use weird filenames
- interrupt the process halfway through

And they make sure the tool still behaves like a professional piece of software.

---

## 22. Starter checklist you can copy into a real repo

```markdown
# CLI Testing Checklist

## Unit
- [ ] validators
- [ ] parsers
- [ ] controller routing
- [ ] renderers
- [ ] exit-code mapping

## Antagonistic
- [ ] blank input
- [ ] whitespace-only input
- [ ] malformed input
- [ ] giant input
- [ ] conflicting flags
- [ ] missing files
- [ ] invalid config
- [ ] stdout/stderr split
- [ ] rerender does not append stale content
- [ ] EOF / interrupt handling

## E2E
- [ ] --help works
- [ ] valid command succeeds
- [ ] invalid command fails nonzero
- [ ] runtime failure fails nonzero
- [ ] interactive flow works
```

---

## 23. Suggested next step

Turn this file into a repo-specific skill by adding:

- the exact way your CLI is invoked
- your project’s exit-code policy
- your rendering contract
- your MVC boundaries
- your known historical bug classes

