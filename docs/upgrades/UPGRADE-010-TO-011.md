# Upgrade from Build 010 to Build 011

## Git workflow

Commit or stash local changes before updating.

```bash
git status
git add .
git commit -m "chore: preserve local Build 010 changes"
```

Pull the new build:

```bash
git checkout main
git pull
```

Activate the existing environment:

```bash
source .venv/bin/activate
```

Refresh the editable installation:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"
```

Run tests:

```bash
pytest -v
```

Start the application:

```bash
zerorodcad-desktop
```

## Project compatibility

Build 011 continues to use `.zerorod` file format version 1. Existing Build 010 projects can be opened without conversion.

## First validation

1. Open `examples/cbg-open-g.zerorod`.
2. Confirm the body appears in the preview.
3. Drag to rotate.
4. Use the mouse wheel to zoom.
5. Toggle Rod and Strings.
6. Change body depth from 9.0 to 10.0 mm.
7. Wait for the preview to rebuild.
8. Export STL and STEP.
9. Inspect both files independently.
