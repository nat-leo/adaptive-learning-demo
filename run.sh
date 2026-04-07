#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_python() {
  local candidate
  for candidate in python3.13 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

if ! PYTHON_BIN="$(find_python)"; then
  echo "Python 3.13+ is required but no python3 interpreter was found." >&2
  exit 1
fi

if ! "${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)'; then
  echo "Python 3.13+ is required. Found: $("${PYTHON_BIN}" -V 2>&1)" >&2
  exit 1
fi

exec "${PYTHON_BIN}" "${REPO_ROOT}/src/adaptive_learning/cli.py" "$@"
