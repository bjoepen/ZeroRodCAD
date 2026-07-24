.PHONY: setup test lint format quality app example hooks
setup:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip setuptools wheel
	. .venv/bin/activate && python -m pip install -e ".[dev,desktop]"
test:
	pytest -v
lint:
	ruff check .
format:
	ruff format .
quality:
	ruff check .
	ruff format --check .
	pytest -v
	pre-commit run --all-files
hooks:
	pre-commit install
app:
	zerorodcad-desktop
example:
	zerorodcad-build examples/cbg-open-g.zerorod -o exports
