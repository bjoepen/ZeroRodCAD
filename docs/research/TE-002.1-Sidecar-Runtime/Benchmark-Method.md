# TE-002.1 — Benchmark Method

Tool: `tools/poc/tauri/benchmark_sidecar_runtime.py`, stdlib-only (no new dependency — `subprocess`,
`os`, `statistics`, `json`, `pathlib`). Two subcommands: `oneshot` (Variants A/B) and `persistent`
(Variants C/D). Every run writes a JSON report under `build/reports/te0021-sidecar-runtime/` plus a
human-readable summary on stderr.

## One-shot benchmark (`bench_oneshot`)

Spawns the binary fresh, sends one `preview` request, reads the response, waits for exit — 20
times per variant (the mandate's "≥10, better 20" requirement). Records the full wall-clock
round trip for each run (`raw_durations_seconds`), then reports `min`/`median`/`p95`/`max` via
`statistics.quantiles` — never a single averaged number, since a single mean would hide the
variance that turned out to matter (Variant A's max was more than 2× its min).

## Persistent benchmark (`bench_persistent`)

Spawns the binary once with `--persistent`, sends a `preview` request (recorded separately as
`cold_start_seconds` — this is the only request that pays process-startup cost), then sends 19
more `preview` requests to the same already-running process (`raw_warm_durations_seconds`,
reported the same min/median/p95/max way), takes an RSS snapshot after requests 1/5/10/20, then
sends `shutdown` and confirms clean exit. Cold and warm are always reported and analyzed
separately — mixing them into one distribution would have hidden exactly the effect being
measured (cold-start cost dominated by packaging, warm cost dominated by actual engine work).

## RSS measurement — a real methodology bug found and fixed mid-benchmark

The first Variant C run reported a flat ~1.6 MB RSS across all 20 requests, despite the sidecar
doing real `cadquery`/OCP/`numba`/`scipy` work each time. Manual process-tree inspection
(`pgrep -P <pid>`) showed why: a PyInstaller **onefile** executable's own process is a lightweight
bootloader that self-extracts and then forks/execs a *separate child process* that does the actual
work. Measuring only the top-level PID measures the bootloader, not the worker — a near-empty
process that never changes. onedir builds do not fork at all (single process, so this bug never
showed up in Variant B/D's original numbers).

Fixed in `_rss_kb()`: it now walks the process tree (`_child_pids()`, up to 5 levels deep) to the
deepest live descendant before reading RSS via `ps`. Variant A/B's RSS *snapshots* (a single
before/after-spawn number, not the full 20-run timing benchmark) were re-taken with the fixed
function; their timing numbers were untouched since only the RSS measurement was ever wrong.
Variant C's complete benchmark (cold start, 19 warm requests, 4 RSS checkpoints) was re-run in
full with the fix in place — the numbers in `Memory.md`/`Performance.md` for Variant C are the
corrected run, not the original flat-1.6MB one.

## Deployment footprint

`_dir_size_and_count()` walks the actual built artifact on disk (`du`-equivalent, stdlib
`os.walk` + `os.path.getsize`) and counts files — used for onefile (1 file always) vs. onedir
(hundreds of files in `_internal/`) comparison in `Packaging.md`.

## What was deliberately not done

No synthetic/mocked sidecar — every benchmark run drives the real compiled binary through the
real protocol, doing the real `zerorodcad` model build and tessellation. No cross-machine
comparison (single host, back-to-back runs, controlled variable = packaging/runtime mode only).
No attempt to reduce Variant A's cold-start variance (max 30.4 s vs. min 15.3 s) — it's reported
as measured, including the outlier, not smoothed over.
