# Changelog

## Build 011.2 – Formatter Compliance

### Fixed

- Applied the exact Ruff formatter output to all six reported files.
- Removed the leading blank line in `zerorodcad_desktop/__init__.py`.
- Normalized line wrapping in parameter, preview, report and desktop modules.

### Compatibility

- No geometry parameters changed.
- `.zerorod` project format remains version 1.
- Existing Build 010, 011 and 011.1 projects remain compatible.

## Build 011.1 – Quality Gate

### Fixed

- Removed unnecessary quotes from `ZeroRodParameters.from_dict()`.
- Added `strict=True` to related `zip()` operations.
- Moved `Iterable` to `collections.abc`.
- Resolved all four Ruff findings reported against Build 011.

### Added

- Pre-commit configuration.
- Ruff lint and format hooks.
- JSON, TOML and YAML checks.
- Trailing-whitespace and end-of-file checks.
- Large-file protection.
- Upgrade and validation instructions.

### Compatibility

- No geometry parameter changes.
- `.zerorod` project format remains version 1.
- Existing Build 010 and 011 project files remain compatible.
