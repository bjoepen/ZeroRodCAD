# TE-002.1 — Performance

All times in seconds, measured by `tools/poc/tauri/benchmark_sidecar_runtime.py` on the same host,
back-to-back, one variant after another. Raw JSON: `build/reports/te0021-sidecar-runtime/variant-*.json`.

## Variant A — onefile, one-shot (20 runs)

| min | median | p95 | max |
|---|---|---|---|
| 15.265 | 15.789 | 18.820 | 30.423 |

Every single request pays full PyInstaller self-extraction. High variance (max is ~2× min) —
not smoothed over; reported as measured.

## Variant B — onedir, one-shot (20 runs)

| min | median | p95 | max |
|---|---|---|---|
| 0.754 | 0.768 | 0.787 | 0.855 |

No self-extraction. ~20× faster median than Variant A, from the packaging change alone — nothing
else differs between A and B.

## Variant C — onefile, persistent (1 cold start + 19 warm requests)

- Cold start (first request, includes onefile self-extraction): **17.305 s**
- Warm round trip (requests 2–20):

| min | median | p95 | max |
|---|---|---|---|
| 0.1279 | 0.1307 | 0.1347 | 0.1350 |

## Variant D — onedir, persistent (1 cold start + 19 warm requests)

- Cold start (first request, no self-extraction needed): **0.644 s**
- Warm round trip (requests 2–20):

| min | median | p95 | max |
|---|---|---|---|
| 0.1256 | 0.1290 | 0.1312 | 0.1316 |

## Engine work itself (measured inside the sidecar, all variants)

- Model build + tessellation: ~0.13–0.15 s
- JSON serialization: ~0.0003 s

This confirms the same finding TE-002 already made: the actual CAD/tessellation/serialization
work is fast and constant across all four variants (~0.13–0.15 s) — every meaningful difference
between variants is a **process-startup packaging** effect, not an engine or protocol effect.

## What this means combined

- Warm-request latency is nearly identical whether the process is onefile- or onedir-packaged
  (C: 0.131 s median, D: 0.129 s median) — once a process is already running, packaging mode
  essentially doesn't matter.
- Cold-start cost is where packaging matters enormously: onefile costs ~15–17 s per cold start
  (one-shot: every request; persistent: only the first), onedir costs under a second either way.
- Persistent transport turns Variant A's ~15.8 s median cost into a one-time ~17.3 s (C) or
  ~0.64 s (D) cost, after which every subsequent request is ~0.13 s — a ~120× improvement over
  Variant A's per-request cost once the process is warm.
