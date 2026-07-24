# Build 012 – Native macOS Application Foundation

## Objective

Provide a transparent and reproducible path from the Python repository to a real macOS application bundle.

## Scope

Build 012 introduces:

- application metadata,
- application icon,
- project-file registration,
- diagnostics,
- macOS packaging,
- bundle verification,
- release ZIP generation.

## Packaging architecture

```text
Repository
    │
    ├── PySide6 + CadQuery application
    ├── application icon PNG
    ├── PyInstaller specification
    └── macOS build scripts
            │
            ▼
    ZeroRodCAD Desktop.app
            │
            ▼
    Release ZIP
```

## Why the `.app` is not prebuilt in this repository package

A reliable macOS application must be:

1. built on macOS,
2. tested on the target architecture,
3. inspected for included CadQuery/OCP libraries,
4. optionally signed with the owner's Developer ID,
5. optionally notarized through Apple's service.

The repository therefore contains the complete reproducible build system but does not claim a validated `.app` until those local steps have been completed.

## Definition of Done

- [x] Application metadata centralized.
- [x] PyInstaller specification included.
- [x] Application icon source included.
- [x] `.icns` generation automated.
- [x] `.zerorod` file declaration included.
- [x] About dialog included.
- [x] Diagnostics included.
- [x] Build and verification scripts included.
- [x] Release archive script included.
- [x] Documentation included.
- [ ] `.app` built on the repository owner's Mac.
- [ ] Packaged diagnostics passed.
- [ ] STL and STEP exported from packaged app.
- [ ] Apple signing completed.
- [ ] Apple notarization completed.
