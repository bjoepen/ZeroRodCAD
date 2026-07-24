# Upgrade from Build 011 to Build 011.1

```bash
git status
git checkout main
git pull
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"
pre-commit install
ruff check .
ruff format --check .
pytest -v
pre-commit run --all-files
zerorodcad-desktop
```

Existing `.zerorod` files remain compatible without conversion.
