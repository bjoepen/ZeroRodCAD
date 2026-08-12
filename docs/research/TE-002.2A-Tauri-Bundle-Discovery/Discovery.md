# TE-002.2A — Discovery

Discovery-only evaluation, branch `spike/te0022a-tauri-bundle-discovery` (from
`spike/te0021-sidecar-runtime` @ `4ee5d84`, working tree clean at start). No source code, build
configuration, dependency, or architecture change was made. The existing TE-002.1 app bundle was
analyzed as-is and confirmed byte-for-byte unmodified before and after analysis (see
"Bundle integrity" below).

## Research question

Why is the real, built TE-002.1 Tauri app approximately 700 MB, against the working No-VTK
PySide6 reference of 380.12 MiB (TE-001.2, user-confirmed functional)? This document and its
siblings quantify the composition; they do not propose or perform any removal — that is explicitly
reserved for a later TE-002.2B.

## Target app and bundle integrity

```
experiments/te002-tauri/src-tauri/target/release/bundle/macos/ZeroRodCAD TE-002.1.app
```

Confirmed to exist; **not rebuilt** for this evaluation. SHA-256 of the sorted, concatenated
per-file hashes of all 372 files, taken before and after every analysis step in this session:
`1551b4a7767e42dee6d71033b454ad079ebfc2cf727bda39a7109cb7c33c1248` — identical before and after.
Scanner 2.0 itself independently confirms: *"Das App-Bundle wurde nicht verändert."*

## Tools used (all pre-existing, none built for this evaluation)

- `du -sh` / `du -sk` / `du -A` (apparent size) and `find` + `stat` for cross-checked size
  measurement in multiple units (see `Bundle-Composition.md` for why they differ slightly).
- `tools/scan_bundle.py` (Scanner 2.0, `src/zerorod_analysis/scanner`) — the same tool TE-001.2
  used against the PySide6 bundle, run here with `--dead-libraries --macho-dependencies --no-cache`
  against the Tauri bundle for a directly comparable category breakdown.
- A short, one-off Python script (stdlib `hashlib`/`os.walk` only) for hash-based duplicate-file
  detection — not a new analysis framework, just a filter over Scanner 2.0's file inventory logic
  applied ad hoc, since Scanner 2.0 itself does not do content-hash duplicate detection.
- The existing TE-002.1 runtime trace (`build/reports/te0021-sidecar-runtime/runtime-trace/
  persistent-onedir-trace.json`) — reused verbatim, not re-captured, to classify which bundled
  Python packages were actually observed during a real `preview` request.

## Prior evidence reused, not reproduced

- TE-001.2's `Bundle-Analysis.md`/`Size-Comparison.md` — the 380.12 MiB No-VTK PySide6 baseline's
  own Scanner 2.0 category breakdown, used directly for the delta comparison in
  `Delta-Analysis.md` rather than re-measuring that bundle.
- TE-002.1's `Packaging.md`/`Results.md` — the onefile-vs-onedir deployment footprint numbers and
  the hash-verified no-VTK/no-PySide6 evidence for the exact bundled onedir sidecar binary.
- TE-002.1's persistent-onedir runtime trace — reused for the OBSERVED/NOT-OBSERVED classification
  in `Candidates.md`, not re-captured.

No TE-001/TE-001.1/TE-001.2/TE-002/TE-002.1 benchmark or evidence-gathering step was repeated.
