# ZeroRodCAD Desktop

> **Engineering the Perfect String Path**

**ZeroRodCAD Desktop** is an open-source engineering application for designing parametric zero-fret and string-guide systems for Cigar Box Guitars and related string instruments.

Instead of modifying CAD geometry manually, users describe the instrument through measurable parameters. ZeroRodCAD calculates the resulting geometry, checks the design and exports STL, STEP and a Markdown instrument report.

## Current build

**Build 011.2 — Formatter Compliance**

Build 011.2 retains the interactive workspace and quality gate while applying the canonical Ruff formatting:

- all Ruff findings from Build 011 resolved,
- strict sequence checks for related parameter collections,
- pre-commit hooks for linting, formatting and repository hygiene,
- live recalculation after parameter changes,
- grouped parameter editor,
- interactive 3D preview without an additional rendering dependency,
- drag to rotate,
- mouse wheel to zoom,
- body, rod and virtual-string visibility controls,
- rendered validation and report view,
- asynchronous preview generation,
- stale calculation protection,
- STL and STEP export,
- human-readable `.zerorod` project files.

The 3D preview is intended for design inspection. Manufacturing files remain the authoritative geometry.

## Default reference model

| Parameter | Value |
|---|---:|
| Body width | 38.00 mm |
| Body depth | 9.00 mm |
| Fretboard height | 6.90 mm |
| Rod diameter | 3.00 mm |
| Groove diameter | 2.94 mm |
| String count | 3 |
| String gauges | .036 / .026 / .017 in |
| String spacing | 10.00 mm |
| String inlet height | 2.80 mm |

## Quick start on macOS

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd ZeroRodCAD-Desktop

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop]"

pytest -v
zerorodcad-desktop
```

Existing Build 010 users can update in place:

```bash
git pull
source .venv/bin/activate
python -m pip install -e ".[dev,desktop]"
pytest -v
zerorodcad-desktop
```

Detailed instructions: [`docs/INSTALL_MACOS.md`](docs/INSTALL_MACOS.md)

## Desktop controls

- Change a parameter: the report updates immediately and the model is rebuilt after a short delay.
- Drag inside the preview: rotate the model.
- Mouse wheel: zoom.
- Reset View: restore the default camera.
- Toggle Body, Rod and Strings independently.
- Open and save `.zerorod` projects from the File menu.
- Export STL, STEP and the instrument report from the toolbar or File menu.

## Repository layout

```text
ZeroRodCAD-Desktop/
├── src/
│   ├── zerorodcad/
│   └── zerorodcad_desktop/
├── tests/
├── docs/
├── examples/
├── exports/
├── scripts/
└── .github/
```

## Engineering philosophy

1. **Parametric first** — geometry is generated from parameters.
2. **Instrument first** — design decisions serve the instrument.
3. **Prototype driven** — important changes require physical validation.
4. **Transparent engineering** — changes and evidence are documented.
5. **Open source** — improvements benefit the maker community.

## Project status

The project is under active development. The interactive preview has been implemented without adding PyVista or VTK, keeping the installation compact and compatible with the existing CadQuery/PySide6 environment.

## License

MIT License. See [`LICENSE`](LICENSE).


## Pre-commit quality gate

Install once:

```bash
pre-commit install
```

Run all checks:

```bash
pre-commit run --all-files
```
