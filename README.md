# ZeroRodCAD Desktop

> **Engineering the Perfect String Path**

**ZeroRodCAD Desktop** is an open-source engineering application for designing parametric zero-fret and string-guide systems for Cigar Box Guitars and related string instruments.

## Current build

**Build 012 — Native macOS Application Foundation**

Build 012 adds the complete repository infrastructure needed to produce a real macOS `.app` bundle:

- PyInstaller macOS specification,
- native application metadata,
- `.zerorod` file-type declaration,
- macOS application icon,
- build, verification and release scripts,
- About and Diagnostics dialogs,
- `--diagnose` command-line mode,
- drag-and-drop opening of `.zerorod` projects,
- remembered project/export directory,
- native Help menu,
- packaging and release documentation.

The source application remains directly runnable with:

```bash
zerorodcad-desktop
```

The packaged application is built locally on macOS because macOS bundles must be created and verified on macOS.

## Quick start

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd ZeroRodCAD-Desktop

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev,desktop,packaging]"

pre-commit install
make quality
zerorodcad-desktop
```

## Build the `.app`

```bash
./scripts/build_macos_app.sh
```

Result:

```text
dist/ZeroRodCAD Desktop.app
```

Verify it:

```bash
./scripts/verify_macos_app.sh
```

Create a distributable ZIP:

```bash
./scripts/package_macos_release.sh
```

Result:

```text
release/ZeroRodCAD-Desktop-0.12.0-macOS.zip
```

## Desktop features

- interactive 3D preview,
- live validation,
- STL and STEP export,
- `.zerorod` project files,
- drag-and-drop project opening,
- native macOS menus,
- runtime diagnostics,
- About dialog,
- remembered file locations.

## Engineering notice

The interactive preview is an inspection aid. STL, STEP, slicer inspection, dimensional measurement and a physical prototype remain mandatory before use.

## License

MIT License. See [`LICENSE`](LICENSE).
