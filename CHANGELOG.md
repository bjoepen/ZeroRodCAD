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
