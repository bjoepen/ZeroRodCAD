# Installation on macOS

## Requirements

- macOS on Intel or Apple Silicon
- Python 3.11 or 3.12
- Terminal
- optional: GitHub Desktop or Git CLI

Python 3.14 is intentionally excluded from this build because binary CAD and GUI dependencies may lag behind a newly released Python version.

## Install Python 3.12 with Homebrew

```bash
brew install python@3.12
```

## Clone and set up the repository

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd ZeroRodCAD-Desktop

/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"
```

On an Intel Mac, `python3.12` may be located somewhere other than `/opt/homebrew/bin/`. Check with:

```bash
which python3.12
```

## Test the engine

```bash
pytest -v
```

## Start the desktop application

```bash
zerorodcad-desktop
```

Alternative:

```bash
python -m zerorodcad_desktop.app
```

## Build an example project from the terminal

```bash
zerorodcad-build examples/cbg-open-g.zerorod -o exports
```

## Reopen the environment later

```bash
cd ZeroRodCAD-Desktop
source .venv/bin/activate
zerorodcad-desktop
```

## Confirm the active interpreter

```bash
python --version
which python
```

The path should point into `.venv/bin/python`.
