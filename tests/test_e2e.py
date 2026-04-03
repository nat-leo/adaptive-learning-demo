from __future__ import annotations

import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest


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


def _drain_pty_until_exit(master_fd: int, process: subprocess.Popen[str], timeout: float = 3.0) -> str:
    deadline = time.monotonic() + timeout
    chunks: list[str] = []

    while time.monotonic() < deadline:
        ready, _, _ = select.select([master_fd], [], [], 0.05)
        if master_fd in ready:
            chunk = os.read(master_fd, 4096)
            if not chunk:
                break
            chunks.append(chunk.decode("utf-8", errors="ignore"))

        if process.poll() is not None and master_fd not in ready:
            break

    return "".join(chunks)


@pytest.mark.skipif(os.name == "nt", reason="PTY interaction test requires POSIX terminals.")
def test_cli_quits_immediately_when_user_presses_q() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cli_path = repo_root / "src" / "adaptive_learning" / "cli.py"
    master_fd, slave_fd = pty.openpty()

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
        _read_until(master_fd, "Adaptive Learning Demo")
        os.write(master_fd, b"q")
        transcript = _drain_pty_until_exit(master_fd, process, timeout=3.0)
        process.wait(timeout=3.0)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3.0)
        os.close(master_fd)

    assert process.returncode == 1
    assert "Quiz ended early. Score: 0/" in transcript
