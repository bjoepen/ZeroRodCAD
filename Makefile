.PHONY: setup test lint format quality app diagnose example hooks macos-app macos-verify macos-release

setup:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip setuptools wheel
	. .venv/bin/activate && python -m pip install -e ".[dev,desktop,packaging]"

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

diagnose:
	zerorodcad-desktop --diagnose

example:
	zerorodcad-build examples/cbg-open-g.zerorod -o exports

macos-app:
	./scripts/build_macos_app.sh

macos-verify:
	./scripts/verify_macos_app.sh

macos-release:
	./scripts/package_macos_release.sh
