# GitHub Workflow – Build 014

```bash
source .venv/bin/activate

ruff check . --fix
ruff format
pytest -v
pre-commit run --all-files

git status
git diff

git add .
git commit -m "build(014): restore preview and stabilize macOS runtime"
git push origin main
```

Tag only after source and packaged previews both pass:

```bash
git tag -a v0.14.0 -m "ZeroRodCAD Desktop 0.14.0"
git push origin v0.14.0
```
