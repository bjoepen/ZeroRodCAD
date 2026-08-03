#!/bin/sh
set -eu

python -m pytest
python -m compileall tools src tests
ruff check --fix
ruff format
ruff check
ruff format --check
pre-commit run --all-files
