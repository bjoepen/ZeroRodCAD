# Upgrade from Build 013 to Build 014

## Clean old artifacts

```bash
rm -rf build dist release .venv-packaging
```

## Refresh development environment

```bash
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"
pre-commit install
```

## Apply and verify repository quality

```bash
ruff check . --fix
ruff format
pytest -v
pre-commit run --all-files
```

## Validate the source preview first

```bash
zerorodcad-desktop
```

Do not continue to packaging until the body, rod and virtual strings appear.

## Build packages

```bash
make packaging-venv
make macos-debug
make macos-app
make macos-verify
```

## Failure log

```bash
cat ~/Library/Logs/ZeroRodCAD/zerorodcad.log
```
