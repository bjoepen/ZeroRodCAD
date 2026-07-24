# Build 011.2 – Formatter Compliance

## Objective

Apply the canonical output expected by `ruff format --check .` after Build 011.1.

## Changed files

- `src/zerorodcad/parameters.py`
- `src/zerorodcad/preview.py`
- `src/zerorodcad/report.py`
- `src/zerorodcad_desktop/__init__.py`
- `src/zerorodcad_desktop/main_window.py`
- `src/zerorodcad_desktop/preview_widget.py`

## Engineering impact

Formatting only. No intentional behavior or geometry change.

## Local validation

```bash
ruff check .
ruff format --check .
pytest -v
pre-commit run --all-files
```
