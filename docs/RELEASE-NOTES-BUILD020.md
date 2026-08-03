# Release Notes — Build 020

Build 020 consolidates the existing bundle analyzer into a reusable architecture. It introduces no
new detection rules or automatic optimization behavior.

- Core logic now lives in `zerorod_analysis`; legacy tool imports delegate.
- One four-stage pipeline owns analysis ordering and intermediate reuse.
- One report engine owns JSON, Markdown, and DOT rendering plus safe atomic writes.
- Per-run pipeline and report metrics expose durations and structural invocation counts.
- The benchmark CLI provides hardware-dependent diagnostics with a stable v1 JSON schema.
- Scanner CLI and benchmark identify the release as Build 020-M4 from one metadata source.

All established CLI arguments, public API calls, report filenames, risk rules, and bundle-health
rules remain compatible. HTML/PDF output, automatic bundle mutation, and a persistent Mach-O cache
are not included.
