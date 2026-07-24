# Validation – Build 015

## Source gate

```bash
source .venv/bin/activate
make quality
python scripts/verify_preview_engine.py
zerorodcad-desktop
```

## Dependency gate

```bash
make packaging-venv
make dependency-audit
```

## Packaging gate

```bash
make macos-debug
make macos-app
make macos-verify
```

## Manual gate

- Open the packaged release application.
- Confirm body, rod and strings are visible.
- Change body depth.
- Confirm preview rebuild.
- Export STL.
- Export STEP.
- Inspect both exports independently.

## Size evidence

Record:

```bash
du -sh "dist/ZeroRodCAD Desktop.app"
```

and preserve all files under:

```text
build/reports/
```
