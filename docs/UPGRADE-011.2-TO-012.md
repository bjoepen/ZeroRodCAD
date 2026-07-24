# Upgrade from Build 011.2 to Build 012

## 1. Update the repository

```bash
git status
git checkout main
git pull
```

## 2. Activate the existing environment

```bash
source .venv/bin/activate
```

## 3. Refresh dependencies

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop,packaging]"
```

## 4. Refresh pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

## 5. Run the quality gate

```bash
ruff check .
ruff format --check .
pytest -v
```

## 6. Start the source application

```bash
zerorodcad-desktop
```

## 7. Run diagnostics

```bash
zerorodcad-desktop --diagnose
```

## 8. Build the macOS application

```bash
./scripts/build_macos_app.sh
```

## 9. Verify the bundle

```bash
./scripts/verify_macos_app.sh
```

## 10. Create a release archive

```bash
./scripts/package_macos_release.sh
```

## Compatibility

The `.zerorod` project format remains version 1. Existing projects require no migration.
