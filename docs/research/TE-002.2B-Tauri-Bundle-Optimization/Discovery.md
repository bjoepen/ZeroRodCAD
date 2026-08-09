# TE-002.2B — Discovery

Branch `spike/te0022b-targeted-bundle-optimization`, from `spike/te0022a-tauri-bundle-discovery`
@ `5102ed1`, working tree clean at start. Unlike TE-002.2A (discovery-only), this evaluation is
authorized to modify and rebuild — every change below is a measured, evidence-driven step, not a
speculative cleanup (`docs/research/TE-002.2A-Tauri-Bundle-Discovery/Candidates.md`).

## Research question

How far can the Tauri v2 bundle be safely reduced without losing functionality, runtime
stability, or the No-VTK/No-PySide6 property — and which of TE-002.2A's five candidates
(duplicate onefile sidecar, duplicate dylibs, llvmlite, numba, scipy) are actually safe to act on?

## Baseline (reused from TE-002.2A, re-verified byte-for-byte before any change)

706,051,017 bytes = 673.34 MiB, 372 files, at
`experiments/te002-tauri/src-tauri/target/release/bundle/macos/ZeroRodCAD TE-002.1.app`.

## Method discipline

Every accepted optimization below was: (1) evidence-gathered first, (2) changed as a single
isolated variable, (3) rebuilt for real (PyInstaller for the sidecar, `tauri build` for the full
app — no artifact was hand-edited and re-measured), (4) functionally validated against the real
`zerorod-sidecar/v1` protocol, (5) measured with the same `find`+`stat -f%z` byte-sum methodology
TE-002.2A used (not `du`, which reports disk blocks and is sensitive to APFS clone/compression
effects that would misrepresent symlink-based dedup — see `Optimization-B-Dylibs.md`).

## Two infrastructure gaps found and closed before any optimization work

1. **The real sidecar protocol cannot exercise "preview with alternate parameters" or
   "STL/STEP export."** `tools/poc/tauri/sidecar/main.py`'s `preview` command rejects any
   non-empty `parameters` (`SidecarError("unsupported_parameters", ...)`), and `COMMANDS` has no
   export command at all — those workflows only exist at the `zerorodcad` library level. See
   `Runtime-Evidence.md`.
2. **`tools/trace_runtime.py` cannot be pointed at the sidecar directly** — it requires a `.app`
   bundle with `Contents/MacOS/<CFBundleExecutable>`, and the Tauri Rust binary has no
   `--startup-test` flag. A new driver, `tools/poc/tauri/capture_runtime_trace.py`, reuses
   `trace_runtime.py`'s own evidence-extraction functions (`_read_raw`, `parse_dyld_output`,
   `merge_evidence`, `RuntimeTrace`, `write_trace_atomic`) against the sidecar binary directly —
   not a new trace engine, the same pipeline wired to a different entry point.

## What TE-002.2A already answered, not re-investigated here

OCP/casadi/nlopt/numpy/ezdxf status (all OBSERVED/REQUIRED, out of scope per the mandate), the
existing category-level bundle composition, and the historical PySide6 delta comparison — all
reused as-is from `docs/research/TE-002.2A-Tauri-Bundle-Discovery/`.
