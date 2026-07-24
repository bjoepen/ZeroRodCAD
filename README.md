# ZeroRodCAD Desktop

> **Engineering the Perfect String Path**

## Current build

**Build 014 — Preview Recovery**

Build 014 restores the 3D preview and stabilizes the macOS application before any further size optimization.

## Corrected defects

- Preview worker signal mismatch fixed: `completed` is used consistently.
- GUI preview types moved into `preview_data.py`.
- Opening the main window no longer imports CadQuery/OCP through the preview widget.
- CadQuery is loaded only inside the background preview worker or export operation.
- Preview failures are written to the application log.
- Build metadata tests updated to 0.14.0 / Build 014.
- Ruff import ordering corrected.
- `make macos-verify` error 141 corrected.
- VTK is retained because the current CadQuery stack imports `vtkmodules` during normal shape operation.

## Important packaging decision

Build 014 deliberately does **not** remove VTK from the application bundle. Removing it before migrating to a verified VTK-free CAD stack can break CadQuery import, tessellation and therefore the 3D preview.

The large application size is recorded as an open engineering issue rather than being “fixed” by deleting required runtime libraries.

## Clean validation

```bash
rm -rf build dist release .venv-packaging

source .venv/bin/activate
python -m pip install -e ".[dev,desktop]"

ruff check . --fix
ruff format
pytest -v
pre-commit run --all-files

zerorodcad-desktop
```

The source application must show the preview before packaging proceeds.

Then:

```bash
make packaging-venv
make macos-debug
make macos-app
make macos-verify
```

## Diagnostics

```bash
cat ~/Library/Logs/ZeroRodCAD/zerorodcad.log
```

## Compatibility

- project format remains version 1,
- no geometry parameters changed,
- Build 010–013 projects remain compatible.
