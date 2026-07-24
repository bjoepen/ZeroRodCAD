.PHONY: setup test lint format quality app diagnose startup-test example hooks packaging-venv dependency-audit preview-verify macos-app macos-debug macos-verify macos-release

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
	ruff check . --fix
	ruff format
	pytest -v
	pre-commit run --all-files

hooks:
	pre-commit install

app:
	zerorodcad-desktop

diagnose:
	zerorodcad-desktop --diagnose

startup-test:
	QT_QPA_PLATFORM=offscreen zerorodcad-desktop --startup-test

example:
	zerorodcad-build examples/cbg-open-g.zerorod -o exports

packaging-venv:
	./scripts/create_packaging_venv.sh

dependency-audit:
	./scripts/audit_dependencies.sh

preview-verify:
	python scripts/verify_preview_engine.py

macos-app:
	./scripts/build_macos_app.sh release

macos-debug:
	./scripts/build_macos_app.sh debug

macos-verify:
	./scripts/verify_macos_app.sh

macos-release:
	./scripts/package_macos_release.sh
