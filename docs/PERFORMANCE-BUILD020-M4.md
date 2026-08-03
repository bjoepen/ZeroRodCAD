# Build 020 M4 Performance

M4 measures structure and elapsed time without changing analysis rules. Every run owns immutable
`PipelineMetrics` and `ReportMetrics`; no global collector or console output is introduced.
`time.perf_counter()` measures the pipeline, each stage, report generation, and each selected
renderer. Regression tests enforce invocation counts and non-negative, internally plausible
durations rather than hardware-specific limits.

## Benchmark

```sh
python tools/benchmark_analysis.py Demo.app --warmup 1 --iterations 5
python tools/benchmark_analysis.py Demo.app --no-cache --json-output /tmp/result.json
```

The tool reports median, minimum, maximum, and mean separately for analysis and reporting, plus
Python, platform, cache state, build ID, warmup, and iterations. Warmups are executed but excluded
from statistics. Cache and report directories are temporary and automatically removed.

## Cache verification

Scanner 2.0's compatible `scanner2-cache.json` remains the only persistent cache. It is initialized
once per analysis and avoids repeated hashing and native-file classification on hits.
`use_cache=False` prevents its reads and writes. The existing Mach-O layer has no persistent cache;
M4 does not introduce a new format. Mach-O inspection and dependency graph construction each occur
once within every pipeline run and are exposed by structural counters.

Benchmark values are hardware-dependent diagnostics, never automatic optimization decisions or
release thresholds. The committed JSON baseline contains only hardware-independent structure.
