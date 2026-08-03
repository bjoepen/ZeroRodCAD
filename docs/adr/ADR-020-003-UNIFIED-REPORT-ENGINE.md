# ADR-020-003: Unified Report Engine

- Status: Accepted
- Date: 2026-08-03

## Context

M2 made analysis sequencing explicit, while Scanner, Mach-O, and dead-library writers still owned
separate filesystem and formatting flows. That duplicated path handling and prevented uniform
atomicity and renderer selection.

## Decision

Use one `ReportEngine` with an immutable explicit registry and one renderer per format: JSON,
Markdown, and DOT. Renderers read only `AnalysisResult`, return data-only rendered models, and never
analyze or write. Render all requested content before validating paths and atomically persisting
UTF-8 files. Keep reporting outside `AnalysisPipeline`.

Adopt `zerorod-analysis/report/v1` as the internal manifest schema ID while retaining the existing
dead-library JSON `schema_version: 2` and the unversioned historical Scanner/Mach-O payload bytes.

## Consequences

- All current analysis reports share selection, collision detection, path safety, and atomic writes.
- Public and compatibility APIs preserve filenames, content, signatures, and tuple order.
- Analysis remains reusable and free of report side effects.
- New formats require a renderer and explicit registry entry.
- The legacy Phase-5 deduplication report remains on its distinct pre-Scanner-2 input model.

## Rejected alternatives

- A report stage was rejected because it would couple analysis to filesystem output.
- Global mutable renderer registration and plugin scans were rejected as nondeterministic.
- Re-analysis inside renderers was rejected because `AnalysisResult` is the sole factual source.
- Direct writes were rejected because failures can expose partial files.
- JSON envelope rewrites were rejected because they would change established payloads.
- HTML and PDF renderers were deferred; M3 adds neither implementation nor dependency.
