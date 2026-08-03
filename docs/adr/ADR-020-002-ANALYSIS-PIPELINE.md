# ADR-020-002: Analysis Pipeline

- Status: Accepted
- Date: 2026-08-03

## Context

M1 placed all analyzer components in one independent package, but `analyze_bundle()` still invoked
Scanner, Mach-O, graph, and dead-library operations directly. Intermediate ownership and stage
preconditions were implicit, making accidental repeated scans or graph builds hard to detect.

## Decision

Use one synchronous `AnalysisPipeline` with four ordered stages and one mutable, run-scoped
`PipelineContext`. Stages implement a small runtime-checkable protocol and mutate only their owned
result fields. The pipeline wraps failures with stage and bundle context while preserving the
original exception as its cause.

Keep `DeadLibraryAnalysisResult` as the runtime result and define `AnalysisResult` as its internal
alias. Keep Scanner 2.0's existing cache as the only persistent cache. Keep report generation
outside stages.

## Consequences

- Execution order and intermediate reuse are explicit and testable.
- Scanner and dependency graph work occur once per standard run.
- No public top-level export, report, rule, CLI, or runtime dependency changes.
- The mutable context must not be reused concurrently or across pipeline runs.
- Future stages require an explicit context field and ordered pipeline insertion.

## Rejected alternatives

- A second analyzer implementation was rejected because it would fork behavior.
- Immutable context copies were rejected because they add churn around large existing mutable
  result objects without a current safety benefit.
- Global stage registries were rejected because they introduce mutable global state and obscure
  order.
- Report-producing stages were rejected because report orchestration belongs to M3.
- A new Mach-O cache was rejected because M1 has no such cache and M2 may not add behavior.
