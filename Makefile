.PHONY: setup test lint app example

setup:
	python3.12 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip setuptools wheel
	. .venv/bin/activate && python -m pip install -e ".[dev,desktop]"

test:
	pytest -v

lint:
	ruff check .

app:
	zerorodcad-desktop

example:
	zerorodcad-build examples/cbg-open-g.zerorod -o exports
