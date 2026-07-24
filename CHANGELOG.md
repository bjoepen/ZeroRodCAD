# Changelog

## Build 017 – Sprint 1: Repository Cleanup

### Added

- Comprehensive `.gitignore`.
- `.gitattributes` with consistent LF handling.
- Documentation index and purpose-based documentation structure.

### Removed

- macOS archive metadata.
- Python caches and generated package metadata.
- Generated export directory from version control.

### Changed

- Historical build notes moved to `docs/releases/`.
- Upgrade notes moved to `docs/upgrades/`.
- Operational documentation moved to `docs/guides/`.
- Architecture and project-format documents moved to `docs/reference/`.

## Build 015 – Lean Runtime Audit

### Added

- Minimal packaging requirements file.
- Separate dependency-audit requirements file.
- Runtime import probe.
- `pipdeptree` text and JSON reports.
- Installed-distribution size report.
- PyInstaller warning and cross-reference report collection.
- Application framework size summary.
- Suspect dependency report.
- Headless preview-engine validation.
- Packaging file tests.

### Packaging changes

- CasADi explicitly excluded.
- llvmlite explicitly excluded.
- Numba explicitly excluded.
- VTK retained.
- OCP retained.
- Clean packaging environment remains mandatory.

### Engineering policy

Dependencies are no longer removed solely because they are large. Removal requires a successful startup, preview, STL and STEP validation sequence.

### Compatibility

- `.zerorod` project format remains version 1.
- No geometry parameters changed.
