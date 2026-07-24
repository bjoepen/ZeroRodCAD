# Changelog

## Build 014 – Preview Recovery

### Fixed

- Restored the preview worker's `completed` signal contract.
- Removed the accidental GUI-startup dependency on `zerorodcad.preview`.
- Added renderer-independent preview data structures.
- Logged full preview tracebacks to the application log.
- Corrected stale Build 012 diagnostics test expectations.
- Corrected Ruff import ordering.
- Fixed macOS verification error 141.

### Packaging

- Retained VTK because the current CadQuery runtime imports `vtkmodules`.
- Reverted unsafe VTK, CasADi and llvmlite pruning.
- Increased the temporary bundle budget to 1.2 GB while a verified lean CAD runtime is investigated.
- Continued excluding unrelated Qt modules and development tooling.

### Compatibility

- `.zerorod` project format remains version 1.
- No geometry parameters changed.
