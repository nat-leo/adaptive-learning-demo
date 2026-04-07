# Testing Strategy (Redo)

This suite is intentionally rebuilt around the current code behavior before any production refactor.

## Goals

- Start with unit tests to verify decision logic and rendering contracts quickly.
- Add a small set of high-value end-to-end tests to validate real CLI wiring.
- Reach approximately 80% total coverage with the fewest tests that still exercise critical branches.

## Why Unit Tests First

Unit tests are the cheapest way to catch regressions in MVC boundaries:

- `models.py`: validation and state transitions (`Question`, `QuizState`, `IncorrectQuestion`, `User.from_dict`).
- `data.py`: file parsing, defaulting, duplicate-ID protection.
- `controller.py`: command routing, scoring/session accounting, retry selection rules, and quit/finish behavior.
- `view.py`: rendering text contracts, key mapping, redraw behavior, and terminal helper behavior.
- `cli.py`: glue code and error-to-exit-code mapping.

This follows the skill guidance: broad unit coverage of decision logic plus targeted CLI hostility checks.

## E2E Scope (Small but High Value)

Only a few e2e tests are included because they are slower and more brittle:

- Non-interactive startup via script path should fail cleanly with exit code `2`.
- Non-interactive startup via module entrypoint (`python -m adaptive_learning`) should fail cleanly.
- PTY test: user pressing `q` immediately exits early with exit code `1`.

These cover the most important user-visible wiring contracts without duplicating unit behavior.

## Intentional Documentation of Current Behavior

Some tests intentionally document current implementation quirks rather than idealized behavior. Example:

- `cli.render_question(...)` currently raises `TypeError` because wrapper keywords do not match `TerminalView.render_question`.

The test preserves that contract as a known issue so a future code fix can be deliberate and reviewed.
