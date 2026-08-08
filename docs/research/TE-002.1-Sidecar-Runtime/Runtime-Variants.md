# TE-002.1 — Runtime Variants

Four packaging/runtime combinations, each built as a real PyInstaller artifact and driven through
the real `zerorod-sidecar/v1` protocol — no variant was simulated or estimated.

| Variant | Packaging | Process model | Built from |
|---|---|---|---|
| A | onefile (`sidecar.spec`) | one-shot (spawn → 1 request → exit) | `tools/poc/tauri/sidecar.spec`, unchanged from TE-002 |
| B | onedir (`sidecar-onedir.spec`) | one-shot | New spec, same hiddenimports/excludes/runtime_hooks as A, `EXE(..., exclude_binaries=True)` + `COLLECT(...)` instead of onefile embedding |
| C | onefile | persistent (spawn once, N requests, explicit `shutdown`) | Same onefile binary as A, launched with `--persistent` |
| D | onedir | persistent | Same onedir build as B, launched with `--persistent` |

## Why a fourth variant at all

The mandate only required D if A/B/C first worked cleanly (no premature scope escalation). They
did, so D was built. It turned out to be the deciding case: C and D have nearly identical warm
request performance and RSS growth (packaging mode barely matters once the process is already
running), but they differ sharply on **cold start** and, more importantly, on **what happens when
Rust has to forcibly kill the process** — see `Process-Lifecycle.md`. Measuring D was not
optional in hindsight; without it, the comparison would have missed the actual deciding factor.

## What stayed identical across all four (for a fair comparison)

- Same CadQuery/OCP versions and the same TE-001.1 patch (`.venv-novtk-bundle`, reused from
  TE-001.2/TE-002, not rebuilt).
- Same `zerorodcad` engine code, same default `ZeroRodParameters`, same `preview` command.
- Same `zerorod-sidecar/v1` request/response schema and `zerorod-mesh/v1` mesh contract.
- Same PyInstaller `hiddenimports`/`excludes`/`runtime_hooks` (only the `EXE`/`COLLECT` packaging
  call differs between the onefile and onedir `.spec` files).
- Same benchmark tool (`tools/poc/tauri/benchmark_sidecar_runtime.py`) and same host machine, run
  back-to-back in the same session.

## What each variant actually is, operationally

- **A (onefile, one-shot)** — TE-002's original approach. Every request pays PyInstaller's
  self-extraction cost (unpacking into a fresh `_MEI*` temp directory) from scratch.
- **B (onedir, one-shot)** — no self-extraction; the executable and its `_internal/` support tree
  are already on disk, so process startup only pays normal OS process-creation cost.
- **C (onefile, persistent)** — pays the onefile self-extraction cost exactly once (at the first
  request), then serves all subsequent requests from the same already-warm process.
- **D (onedir, persistent)** — pays onedir's already-cheap startup cost once, then serves
  subsequent requests the same way as C.

Full numbers: `Performance.md` (latency), `Memory.md` (RSS), `Packaging.md` (disk footprint),
`Process-Lifecycle.md` (shutdown/cleanup behavior), `Results.md` (the combined matrix).
