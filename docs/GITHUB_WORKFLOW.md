# GitHub Workflow

## Publish Build 011.2

```bash
source .venv/bin/activate
python -m pip install -e ".[dev,desktop]"
pre-commit install
ruff check .
ruff format --check .
pytest -v
pre-commit run --all-files
git status
git diff
git add .
git commit -m "build(011.2): apply canonical Ruff formatting"
git push origin main
```
