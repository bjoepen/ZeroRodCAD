# GitHub Workflow – Build 015

## Validate

```bash
source .venv/bin/activate
make quality
python scripts/verify_preview_engine.py
```

## Review

```bash
git status
git diff
```

## Commit

```bash
git add .
git commit -m "build(015): audit and reduce macOS runtime dependencies"
git push origin main
```

Tag only after the packaged preview and exports pass:

```bash
git tag -a v0.15.0 -m "ZeroRodCAD Desktop 0.15.0"
git push origin v0.15.0
```
