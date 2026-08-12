# TE-002.2B — Results

## Performance (final combined candidate vs. TE-002.1 Variant D reference)

Measured via the existing `tools/poc/tauri/benchmark_sidecar_runtime.py persistent` (20 requests),
against the final bundled binary — same tool, same methodology TE-002.1 used.

| Metric | TE-002.1 Variant D (persistent onedir) | TE-002.2B final candidate | Delta |
|---|---:|---:|---:|
| Cold start | 0.644 s | 0.612 s | −0.032 s (no regression; within normal run-to-run noise, if anything marginally faster) |
| Warm median | 0.129 s | 0.1214 s | −0.008 s (no regression) |
| Warm p95 | n/a (not reported in TE-002.1) | 0.1228 s | — |

No performance regression. If anything, both figures come in marginally better than TE-002.1's
own reference numbers — plausibly explained by fewer files for the OS to resolve/mmap at process
start (390 fewer files than the sidecar's original standalone build), though this evaluation does
not claim that as a proven causal mechanism from a single benchmark run.

## Memory (final combined candidate vs. TE-002.1 Variant D reference)

RSS in KB, same `ps`-on-deepest-descendant method, same 4 checkpoints.

| Checkpoint | TE-002.1 Variant D | TE-002.2B final | Delta |
|---|---:|---:|---:|
| after request 1 | 325,248 | 321,056 | −4,192 KB |
| after request 5 | 325,744 | 321,408 | −4,336 KB |
| after request 10 | 326,016 | 321,680 | −4,336 KB |
| after request 20 | 326,384 | 321,904 | −4,480 KB |
| Growth over 20 requests | +1,136 KB (~0.35%) | +848 KB (~0.26%) | — |

No memory regression — steady-state RSS is consistently ~4.2 MB lower (plausibly the numba/scipy
exclusion reducing the process's static working set), and the request-to-request growth rate is in
the same order of magnitude as TE-002.1's own reading, which that evaluation already characterized
as "not enough data to distinguish a real leak from one-time settling" — this evaluation does not
extend that characterization with a longer run either, consistent with the same caveat.

## Combined savings

393.07 MiB / 58.37% off the original 673.34 MiB baseline — see `Size-Comparison.md` for the full
stage-by-stage breakdown.
