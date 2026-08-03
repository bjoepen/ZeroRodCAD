# ADR-020-004: Performance Metrics and Benchmarks

- Status: Accepted
- Date: 2026-08-03

## Context

M1–M3 established a single core, pipeline, and report engine. Build 020 still needed observable
single-execution guarantees and a reproducible way to measure analysis separately from reporting
without treating one developer machine as a universal performance standard.

## Decision

Measure each run with `time.perf_counter()` and immutable per-run metric models. Attach pipeline
metrics optionally to `AnalysisResult`; expose report metrics through an internal
`generate_with_metrics()` call. Provide one internal benchmark function and one developer CLI.
Measure analysis and reporting separately and exclude warmups from statistics.

Use structural regression tests for order and invocation counts instead of tight absolute timing
limits. Commit only a hardware-independent structural baseline. Never trigger automatic
optimization from an individual benchmark value.

## Consequences

- Normal public functions remain compatible and print no diagnostics.
- Failures retain completed timing information where available.
- Benchmark values depend on hardware, OS, Python, cache state, and bundle content.
- Metrics add very small `perf_counter()` overhead without repeating work.
- The benchmark is an internal developer interface, not a fifth stable top-level API export.

## Rejected alternatives

- Global metrics were rejected because concurrent and repeated runs would contaminate each other.
- Wall-clock time was rejected because it is unsuitable for elapsed-duration measurement.
- Strict millisecond release thresholds were rejected as hardware-dependent and flaky.
- Combining analysis and reporting into one number was rejected because it hides the source of a
  regression.
- Automatic removal or optimization based on benchmark results was rejected as unsafe.
