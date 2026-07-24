# Validation

## Source quality gate

```bash
ruff check .
ruff format --check .
pytest -v
pre-commit run --all-files
```

## Source application

```bash
zerorodcad-desktop
zerorodcad-desktop --diagnose
```

## Packaged application

```bash
./scripts/build_macos_app.sh
./scripts/verify_macos_app.sh
```

## Required functional checks

1. Open the example `.zerorod` project.
2. Confirm the preview appears.
3. Rotate and zoom.
4. Change body depth.
5. Confirm asynchronous rebuild.
6. Export STL.
7. Export STEP.
8. Open both files independently.
9. Drag a project onto the app.
10. Confirm the last directory is remembered.

## Release evidence

Store:

- Terminal output,
- diagnostics output,
- screenshot of the packaged app,
- STEP viewer screenshot,
- slicer screenshot,
- prototype measurements.

No packaged release should be described as validated until this evidence exists.
