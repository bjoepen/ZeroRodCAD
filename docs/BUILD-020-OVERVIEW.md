# Build 020 Overview

Build 020 is an architecture release with no new analysis rules:

- M1 extracted the analyzer into `src/zerorod_analysis` and retained legacy facades.
- M2 introduced the four-stage `AnalysisPipeline` and shared context.
- M3 unified JSON, Markdown, and DOT reports behind `ReportEngine`.
- M4 added per-run metrics, reproducible benchmarks, centralized build metadata, and the final gate.

The stable top-level API remains four functions. Analysis is read-only; reporting is a separate,
explicit operation. The desktop GUI and PySide6 remain outside the core. Build 019.3 callers can
upgrade without changing supported imports, CLI arguments, or report filenames.

See `ARCHITECTURE-BUILD020.md`, `PUBLIC-API-BUILD020.md`, `PERFORMANCE-BUILD020-M4.md`, and
`RELEASE-NOTES-BUILD020.md` for the consolidated contracts and limitations.
