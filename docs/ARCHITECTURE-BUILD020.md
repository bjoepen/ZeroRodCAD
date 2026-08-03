# Build 020 M1 Architecture

Build 020 M1 extracts the bundle analyzer from the development-tool namespace into the
standalone `zerorod_analysis` package. The extraction does not change analysis algorithms,
reports, command-line arguments, or user-visible behavior.

The dependency direction is now:

```text
tools/scan_bundle.py ───────────────┐
tools/bundle_analyzer/* wrappers ───┼──> src/zerorod_analysis
future desktop integrations ────────┘
```

`zerorod_analysis` is independent of the desktop application. It imports neither GUI modules
nor PySide6. Scanner data flows to Mach-O dependency analysis, dead-library analysis, advisory
logic, and finally report generation. Internal modules never import from `tools`.

The legacy package contains compatibility wrappers only. They re-export the objects from the
new package, preserving object identity and every established import path.

## Release gate

The milestone is a release candidate only after pytest, compileall, Ruff check and formatting,
and all pre-commit hooks pass on the complete repository. User validation is still required
before declaring it final.
