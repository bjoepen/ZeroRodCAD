# GitHub Workflow

## Publish Build 012

```bash
source .venv/bin/activate
python -m pip install -e ".[dev,desktop,packaging]"

ruff check .
ruff format --check .
pytest -v
pre-commit run --all-files
```

Review:

```bash
git status
git diff
```

Commit:

```bash
git add .
git commit -m "build(012): add native macOS application foundation"
git push origin main
```

## Recommended tag after local `.app` validation

```bash
git tag -a v0.12.0 -m "ZeroRodCAD Desktop 0.12.0"
git push origin v0.12.0
```

Create a GitHub release only after the packaged application has passed the documented macOS validation.
