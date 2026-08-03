# Build 020 M2 Architecture

## Baseline and scope

Build 020 M1 extracted the existing analyzer into `src/zerorod_analysis`. M2 retains every M1
analyzer, rule, report, command-line option, and compatibility import. It adds orchestration only;
there is explicitly no functional analysis change in M2.

The M1 implementation returns `DeadLibraryAnalysisResult` from `analyze_bundle()`. Although the M2
requirements call the central result `AnalysisResult`, changing that runtime type would break the
M1 contract. M2 therefore defines `AnalysisResult` as an internal type alias for the existing class.

## Pipeline

```text
ScannerStage -> MachOStage -> DeadLibraryStage -> AdvisorStage -> AnalysisResult
```

`AnalysisPipeline` owns the ordered stage tuple. Every stage receives the same mutable,
run-scoped `PipelineContext`, executes once, and populates only its assigned fields. No stage writes
reports. `analyze_bundle()` constructs the context and delegates to the default pipeline.

## Context and cache

The context carries bundle and cache configuration, optional report configuration, the scanner
database, Mach-O binaries, dependency graph, dead-library result, advice, health, and warnings. It
contains no analysis behavior and there is no global mutable pipeline state.

M1 has one persistent cache: Scanner 2.0's `scanner2-cache.json`. ScannerStage opens it once and
passes its one database forward. The existing Mach-O implementation has no independent persistent
cache, so M2 does not invent one. `use_cache=False` reaches Scanner unchanged and prevents cache
reads and writes.

## Errors and limits

Missing predecessor data raises `MissingStageResultError`. Other stage failures are re-raised as
`StageExecutionError` with stage name, bundle path, and the original chained cause. Keyboard and
process-control exceptions are not intercepted.

The pipeline remains synchronous and macOS `otool` behavior is unchanged. Report orchestration is
reserved for M3.
