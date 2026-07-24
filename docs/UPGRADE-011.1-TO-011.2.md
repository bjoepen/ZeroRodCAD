# Upgrade from Build 011.1 to Build 011.2

```bash
git checkout main
git pull
source .venv/bin/activate
python -m pip install -e ".[dev,desktop]"
ruff check .
ruff format --check .
pytest -v
pre-commit run --all-files
zerorodcad-desktop
```

The `.zerorod` project format remains unchanged.
