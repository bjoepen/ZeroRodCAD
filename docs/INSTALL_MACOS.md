# Installation on macOS

## Requirements

- macOS on Intel or Apple Silicon
- a working Python version from 3.11 onward
- Terminal
- optional: GitHub Desktop or Git CLI

The repository metadata no longer blocks Python 3.14. Actual compatibility still depends on the CadQuery and PySide6 packages available for the selected Python installation.

## New installation

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd ZeroRodCAD-Desktop

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"
```

## Run tests

```bash
pytest -v
```

## Start the application

```bash
zerorodcad-desktop
```

Alternative:

```bash
python -m zerorodcad_desktop.app
```

## Update an existing installation

```bash
cd ZeroRodCAD-Desktop
git pull
source .venv/bin/activate
python -m pip install -e ".[dev,desktop]"
pytest -v
zerorodcad-desktop
```

## Build the example from the terminal

```bash
zerorodcad-build examples/cbg-open-g.zerorod -o exports
```

## Confirm the active interpreter

```bash
python --version
which python
```

The interpreter path should point into `.venv/bin/python`.

## Troubleshooting

### The application starts but no preview appears

Run from Terminal and inspect the error output:

```bash
zerorodcad-desktop
```

Then verify:

```bash
python -c "import cadquery, PySide6; print('CadQuery and PySide6 imported')"
```

### Editable installation is outdated

```bash
python -m pip install -e ".[dev,desktop]"
```

### Existing environment is inconsistent

```bash
deactivate 2>/dev/null || true
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"
```
