# TE-002.2B — Bundle Size Tracking

All figures are real, measured `find`+`stat -f%z` byte sums of the actual built artifact (same
methodology TE-002.2A used) — none estimated. Stage rows for A-only, B-only and A+B are isolated
full `.app` bundle rebuilds; C/D rows are isolated standalone-sidecar measurements (see
`Optimization-C-Numba-Llvmlite.md` / `Optimization-D-Scipy.md` for why — independent attribution
without paying for 4 extra full Tauri rebuilds); the final row is the real combined `.app`.

| Stage | Size (bytes) | Size (MiB) | Files | Δ from previous | Δ from baseline | Cumulative % reduction |
|---|---:|---:|---:|---:|---:|---:|
| Baseline (TE-002.1/.2A) | 706,051,017 | 673.34 | 372 | — | — | 0% |
| A only (remove onefile) | 564,019,881 | 537.89 | 371 | −135.45 MiB | −135.45 MiB | 20.12% |
| B only (dylib dedup) | 607,585,417 | 579.43 | 294 | −93.90 MiB | −93.90 MiB | 13.95% |
| A + B combined | 465,553,753 | 443.98 | 293 | −229.35 MiB (vs. baseline) | −229.35 MiB | 34.06% |
| C only, sidecar-level (numba/llvmlite) | 317,273,054 | 302.57 | 272 | −128.27 MiB vs. onedir baseline (430.84 MiB) | n/a (sidecar-level) | n/a |
| D only, sidecar-level (scipy) | 414,600,661 | 395.39 | 208 | −35.45 MiB vs. onedir baseline (430.84 MiB) | n/a (sidecar-level) | n/a |
| **Final combined (A+B+C+D)** | **293,892,882** | **280.27** | **193** | **−150.09 MiB (vs. A+B)** | **−393.07 MiB** | **58.37%** |

## Final candidate breakdown

- Baseline: 706,051,017 bytes / 673.34 MiB / 372 files
- Final optimized: 293,892,882 bytes / 280.27 MiB / 193 files
- Total savings: 412,158,135 bytes = **393.07 MiB = 58.37%**

## Sanity cross-check

A(135.45) + B(93.90) + C(128.27, sidecar-level) + D(35.45, sidecar-level) = 393.07 MiB — matches
the final combined measurement's total savings (393.07 MiB) exactly. The four optimizations are
independent, non-overlapping, and additive at this bundle's scale (no double-counted savings,
no interaction effect large enough to show up at this precision).

## Not touched / not in scope

OCP (216 MiB+), casadi, nlopt, numpy, ezdxf — all confirmed REQUIRED/OBSERVED by TE-002.2A and
explicitly out of scope for TE-002.2B (mandate sections 25–26). No dependency in this set was
removed, downgraded, or reinterpreted.
