# Changelog

## Build 012 – Native macOS Application Foundation

### Added

- PyInstaller macOS application specification.
- Native `.app` bundle metadata.
- `.zerorod` file-type declaration and UTI.
- 1024 × 1024 ZeroRodCAD application icon.
- macOS icon-set generation script.
- macOS `.app` build script.
- Packaged-application verification script.
- Release ZIP packaging script.
- About dialog.
- Runtime diagnostics dialog.
- `--diagnose` command-line mode.
- Drag-and-drop opening of `.zerorod` files.
- Remembered project and export directory.
- Native Help menu.
- Packaging, signing and release documentation.

### Changed

- Package version updated to 0.12.0.
- Main window title now reads application metadata centrally.
- Packaging dependencies moved to the optional `packaging` extra.

### Compatibility

- `.zerorod` project format remains version 1.
- No ZeroRod geometry parameters changed.
- Build 010 and Build 011 project files remain compatible.

### Not included

- Apple Developer ID signing.
- Apple notarization credentials.
- A prebuilt universal application bundle.

These tasks require the repository owner's Apple environment and credentials.

## Build 011.2 – Formatter Compliance

- Canonical Ruff formatting.

## Build 011.1 – Quality Gate

- Ruff fixes and automated pre-commit checks.

## Build 011 – Interactive Design Workspace

- Interactive preview and live validation.

## Build 010 – Desktop Foundation

- Initial GitHub repository and desktop interface.
