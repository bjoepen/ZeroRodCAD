# Build 020 M3 Architecture

## Scope

M3 introduces one unified report engine without changing scanning, dependency resolution,
dead-library detection, advice, risk, health, or the M2 pipeline order. Report filenames and report
content remain compatible.

```text
AnalysisResult -> ReportEngine -> JsonRenderer
                               -> MarkdownRenderer
                               -> DotRenderer
```

The M2 runtime-compatible `AnalysisResult` alias remains `DeadLibraryAnalysisResult`. M3 adds
optional references to the already computed scanner database, Mach-O binaries, dependency graph,
advice, and health. The pipeline attaches those existing objects after all four stages; it performs
no additional analysis.

## Separation

`analyze_bundle()` remains read-only and writes no reports. `generate_reports()` is the explicit
filesystem boundary. Reports remain outside `AnalysisPipeline` so analysis can be reused without
output side effects and rendering failures cannot invalidate analysis.

## Compatibility

The public call still emits the five established dead-library reports. Scanner and Mach-O legacy
writers create their established files through scoped `ReportRequest` objects. Compatibility
modules remain delegating facades. The older Phase-5 deduplication report has a different input
model and remains unchanged; M3 does not repeat its analysis in order to force it into
`AnalysisResult`.
