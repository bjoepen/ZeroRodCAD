# Analysis Pipeline Architecture

## Stage contract

Every stage implements the runtime-checkable `AnalysisStage` protocol:

```python
class AnalysisStage(Protocol):
    name: str

    def run(self, context: PipelineContext) -> None: ...
```

The mutable-context form matches the existing mutable `BundleDatabase` and dead-library result
models and avoids copying large bundle indexes. A context belongs to exactly one run.

## Responsibilities

| Stage | Reads | Writes |
|---|---|---|
| ScannerStage | bundle path, filter, cache configuration | BundleDatabase |
| MachOStage | BundleDatabase | Mach-O binaries, DependencyGraph |
| DeadLibraryStage | BundleDatabase, DependencyGraph | DeadLibraryAnalysisResult |
| AdvisorStage | DeadLibraryAnalysisResult | advice tuple, BundleHealth |

Later stages never rescan the bundle or rebuild the dependency graph. Stages do not import report
renderers. `AnalysisPipeline.stage_names` exposes deterministic diagnostics without making pipeline
classes part of the top-level public API.

## Extending the pipeline

A future internal stage should implement the same protocol, declare one unique diagnostic name,
consume only established context fields, and own its output fields. It is then inserted explicitly
in the ordered tuple with contract, order, single-execution, failure, and cache tests. Adding a stage
must not implicitly change the four public functions or report formats.
