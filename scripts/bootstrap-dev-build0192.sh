#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
REQUIREMENTS_FILE="requirements-dev-build0192.txt"

printf 'Repository: %s\n' "$REPOSITORY_ROOT"
printf 'Python: %s\n' "$PYTHON_BIN"
printf 'Environment: %s\n' "$VENV_DIR"

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
  printf 'Fehler: %s wurde im Repository-Stamm nicht gefunden.\n' "$REQUIREMENTS_FILE" >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$REQUIREMENTS_FILE"
python -m pre_commit install

printf '\nBuild-019.2-Entwicklungsumgebung ist bereit.\n'
printf 'In einer neuen Bash-Sitzung aktivieren mit:\n'
printf '  source %s/bin/activate\n' "$VENV_DIR"
printf '\nDanach validieren mit:\n'
printf '  bash scripts/validate-build0192.sh\n'
