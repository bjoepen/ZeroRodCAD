# Upgrade from Build 012 to Build 013

## 1. Replace Build 012 with the complete Build 013 repository

Build 013 is a full repository package.

## 2. Refresh the development environment

```bash
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"
pre-commit install
```

## 3. Quality checks

```bash
ruff check .
ruff format --check .
pytest -v
pre-commit run --all-files
QT_QPA_PLATFORM=offscreen zerorodcad-desktop --startup-test
```

## 4. Remove old application products

```bash
rm -rf build dist release .venv-packaging
```

This is important. Do not reuse the Build 012 PyInstaller output.

## 5. Create the clean packaging environment

```bash
./scripts/create_packaging_venv.sh
```

## 6. Build the debug application first

```bash
./scripts/build_macos_app.sh debug
```

Run it directly:

```bash
"dist/ZeroRodCAD Desktop Debug.app/Contents/MacOS/ZeroRodCAD Desktop" --diagnose
```

## 7. Build and verify the release application

```bash
./scripts/build_macos_app.sh release
./scripts/verify_macos_app.sh
```

## 8. Inspect the log if startup fails

```bash
cat ~/Library/Logs/ZeroRodCAD/zerorodcad.log
```

## 9. Package the release only after validation

```bash
./scripts/package_macos_release.sh
```
