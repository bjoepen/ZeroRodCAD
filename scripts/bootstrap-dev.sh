#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

printf 'Repository: %s\n' "$REPOSITORY_ROOT"
printf 'Python: %s\n' "$PYTHON_BIN"
printf 'Environment: %s\n' "$VENV_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements-dev-build0191a.txt
pre-commit install

printf '\nEntwicklungsumgebung bereit.\n'
printf 'In einer neuen Bash-Sitzung aktivieren mit:\n'
printf '  source %s/bin/activate\n' "$VENV_DIR"
