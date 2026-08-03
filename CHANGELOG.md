# Build 020 M4 — Performance and Release Consolidation

- Added per-run pipeline and report metrics with structural invocation counters.
- Added a reproducible temporary benchmark workflow and stable v1 benchmark schema.
- Centralized Scanner and benchmark build metadata at Build 020-M4.
- Consolidated Build 020 architecture, migration, performance, and release documentation.

# Build 020 M3 — Unified Report Engine

- Unified JSON, Markdown, and DOT generation behind one explicit renderer registry.
- Added safe path validation, collision detection, and atomic UTF-8 writes.
- Routed public and legacy report writers through the engine without changing report filenames.
- Updated Scanner CLI release metadata to Build 020-M3.

# Build 020 M2 — Analysis Pipeline Architecture

- Added the internal Scanner, Mach-O, dead-library, and advisor pipeline with a shared context.
- Routed `analyze_bundle()` through the pipeline without changing its signature or runtime result.
- Added typed stage diagnostics, predecessor checks, single-execution and cache tests.
- Preserved the four-function public API, CLI behavior, report formats, and compatibility imports.

# Changelog – Build 019.2.1

## Behoben

- Fehlende PySide6-Entwicklungsabhängigkeit verursachte Collection-Fehler in Desktop- und Startup-Tests.
- Build 019.2 erhält eine eigene, reproduzierbare Requirements-Datei für das lokale Release-Gate.

## Ergänzt

- `requirements-dev-build0192.txt`
- `scripts/bootstrap-dev-build0192.sh`
- Drop-in- und Git-Commit-Anleitungen

## Unverändert

- Mach-O Dependency Graph
- Scanner 2.0
- `scripts/validate-build0192.sh`
- Repository-Struktur
- Read-only-Verhalten der Analyse
# Build 020 M1 — Core Extraction (Release Candidate)

- Extracted the complete bundle analyzer into `src/zerorod_analysis`.
- Added the four-function public API and retained all legacy analyzer import paths through
  compatibility wrappers.
- Moved Scanner 2.0, Mach-O, dead-library, advisory, reporting, and optimization logic out of
  the tools namespace without changing algorithms or report formats.
- Added public-API, export, compatibility, GUI-independence, PySide6-independence, and import
  architecture tests.
