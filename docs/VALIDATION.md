# Validation – Build 014

## Quality gate

```bash
ruff check . --fix
ruff format
pytest -v
pre-commit run --all-files
```

## Source preview gate

```bash
zerorodcad-desktop
```

Required:

- body visible,
- rod visible,
- three virtual strings visible,
- rotation works,
- zoom works,
- parameter changes rebuild the preview.

## Packaged preview gate

```bash
make packaging-venv
make macos-debug
make macos-app
make macos-verify
```

Open the release app and repeat all source preview checks.

## Export gate

- export STL,
- export STEP,
- inspect both independently,
- record screenshots and bundle size.

A smaller bundle is not accepted as successful if preview or export functionality is lost.
