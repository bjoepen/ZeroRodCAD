# Build 013 – macOS Packaging Recovery

## Problem statement

Build 012 produced an application bundle larger than 1 GB and the bundle did not start.

## Root causes addressed

### Entry point

The former PyInstaller specification executed a package module file directly. That file used relative imports, which are fragile when treated as a standalone script.

Build 013 uses:

```text
zerorodcad_desktop/launcher.py
```

with an absolute package import.

### Startup dependency chain

The main window imported export and preview modules, which imported CadQuery/OCP before the first window appeared. Any missing binary or packaging error therefore caused a silent windowed-app failure.

Build 013 loads CadQuery only when:

- a preview worker starts,
- an STL/STEP export starts.

### Dirty packaging environment

PyInstaller analyses the active environment. A development environment may contain plotting, notebooks, tests and optional Qt modules.

Build 013 always creates `.venv-packaging` with only:

- ZeroRodCAD,
- CadQuery,
- PySide6,
- PyInstaller.

### Oversized Qt collection

The application uses QtCore, QtGui and QtWidgets only. Build 013 explicitly excludes WebEngine, QML, Quick, Multimedia, 3D and other unused modules.

## Definition of Done

- [x] Package-safe launcher.
- [x] Lazy CadQuery startup.
- [x] Debug console app.
- [x] Persistent log.
- [x] Clean packaging environment.
- [x] Bundle size report.
- [x] Size budget.
- [x] Off-screen startup smoke test.
- [ ] Debug app built on macOS.
- [ ] Release app starts on macOS.
- [ ] Preview generation succeeds in packaged app.
- [ ] STL and STEP exports succeed in packaged app.
- [ ] Final bundle size recorded.
