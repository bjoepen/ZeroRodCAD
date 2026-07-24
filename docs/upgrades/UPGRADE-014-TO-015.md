# Upgrade from Build 014 to Build 015

## 1. Remove previous build products

```bash
rm -rf build dist release .venv-packaging
```

## 2. Validate source code

```bash
source .venv/bin/activate
python -m pip install -e ".[dev,desktop]"
pre-commit install
make quality
```

## 3. Create the minimal packaging environment

```bash
make packaging-venv
```

## 4. Generate dependency evidence

```bash
make dependency-audit
```

## 5. Build the debug application

```bash
make macos-debug
```

Run:

```bash
"dist/ZeroRodCAD Desktop Debug.app/Contents/MacOS/ZeroRodCAD Desktop"   --diagnose
```

## 6. Build and verify the release application

```bash
make macos-app
make macos-verify
```

## 7. Manual acceptance

Confirm:

- window opens,
- preview appears,
- preview rebuilds after parameter changes,
- STL export works,
- STEP export works.

## 8. Compare size

```bash
du -sh "dist/ZeroRodCAD Desktop.app"
cat build/reports/macos-bundle-size.txt
cat build/reports/suspect-dependencies.txt
```
