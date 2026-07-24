# Build 010 – Desktop Foundation

## Goal

Create the first transparent, repository-ready ZeroRodCAD Desktop foundation.

## Engineering changes

- Separate CAD engine and GUI.
- Remove the hard dependency on exactly three strings.
- Introduce `.zerorod` project files.
- Introduce one validation API for CLI and GUI.
- Add validated STL/STEP/report export.
- Add repository governance and CI.
- Keep the interactive 3D viewport out of scope until Build 011.

## Definition of Done

- [x] Repository structure created.
- [x] CadQuery engine retained.
- [x] String count generalized.
- [x] Project files implemented.
- [x] Validation API implemented.
- [x] Desktop form implemented.
- [x] Export service implemented.
- [x] Tests included.
- [x] GitHub Actions workflow included.
- [x] macOS setup documented.
- [ ] CadQuery geometry executed locally.
- [ ] GUI tested locally on macOS.
- [ ] STL/STEP inspected in slicer and CAD viewer.
