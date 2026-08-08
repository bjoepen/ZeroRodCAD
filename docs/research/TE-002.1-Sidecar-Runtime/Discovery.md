# TE-002.1 — Discovery

Technology Evaluation, branch `spike/te0021-sidecar-runtime` (from `main`, after TE-002's
`spike/te002-tauri-threejs-preview` was merged). Not a production migration — the existing
PySide6 app (`src/zerorodcad_desktop/`) is completely untouched by this evaluation, and no file
under `src/zerorodcad*`, `packaging/`, or `src/zerorodcad_desktop/` was modified.

## Research question

TE-002 proved the Tauri v2 + Python-sidecar + Three.js architecture works, but flagged two
concrete, non-architectural risks it deliberately did not resolve: a ~15 s onefile sidecar
cold-start cost per request, and no evaluation of whether reusing a single long-lived sidecar
process (instead of spawning a fresh one per request) would be worthwhile. TE-002.1 answers that
directly: **which sidecar runtime/deployment strategy should ZeroRodCAD actually use** — measured
and compared, not assumed.

The most important constraint governing this whole evaluation: **do not prematurely pick a
variant**. The explicit instruction that shaped every phase below was *"NICHT vorschnell eine
Variante auswählen... Messen. Vergleichen. Dokumentieren. Dann Empfehlung ableiten."* ("Don't
prematurely pick a variant... Measure. Compare. Document. Then derive a recommendation.") Every
variant below — including the one eventually recommended — was built and measured, not assumed
superior in advance.

## Variants compared

- **Variant A** — onefile packaging, one-shot process (spawn → one request → exit). This is
  exactly what TE-002 already had; re-measured here as the reference baseline, not reused from
  TE-002's own numbers (a fresh, reproducible 20-run measurement, per the mandate's requirement
  that Variant A not just cite historical figures).
- **Variant B** — onedir packaging, one-shot process. Same engine, same patch, same protocol,
  same parameters as Variant A — the only variable changed is the PyInstaller packaging mode.
- **Variant C** — onefile packaging, persistent process (one long-lived sidecar process serves
  many requests over its lifetime, via a new `--persistent` mode added to the same protocol).
- **Variant D** — onedir packaging, persistent process. Only measured because A/B/C all worked
  cleanly first (the mandate's condition for even attempting this combination) — see
  `Runtime-Variants.md` for why it turned out to matter.

## Prior TE documentation used (not re-investigated)

- **TE-001 / TE-001.1 / TE-001.2** (`docs/research/TE-001*`): the no-VTK CadQuery patch
  (`cadquery` 2.8.0 + the 4-file TE-001.1 patch + `cadquery-ocp-novtk` 7.9.3.1.1), the
  `VTKImportBlocker`, and the real-token `vtk` regex heuristic that avoids flagging
  `cadquery.occ_impl.exporters.vtk` or `tools.poc.novtk.vtk_import_blocker` as false positives.
  All reused verbatim, none redesigned.
- **TE-002** (`docs/research/TE-002-Tauri-ThreeJS/`): the Tauri v2 + Python sidecar + Three.js
  architecture itself, the `zerorod-sidecar/v1` one-shot request/response contract, the
  `zerorod-mesh/v1` mesh contract, and the "process control belongs in Rust, not the WebView"
  boundary (`Tauri-Architecture.md`). TE-002.1 extends this architecture's *runtime strategy*
  only — the contract shape, the IPC boundary, and the mesh format are all unchanged.
- Build 021 M1 runtime trace infrastructure (`tools/poc/novtk/runtime_trace_adapter.py`,
  `vtk_evidence()`) — reused as-is for the final No-VTK/No-PySide6 regression check against the
  chosen variant's bundled artifact.

## Architecture boundary preserved

TE-002's explicit rule — the WebView never spawns a process directly; only Rust does, through a
narrow set of app-registered `#[tauri::command]`s — is unchanged by TE-002.1. The persistent
engine adds two new commands (`persistent_preview`, `persistent_shutdown`), both following the
exact same pattern as TE-002's `request_preview`: the frontend calls `invoke(...)`, Rust owns the
`CommandChild` and all process lifecycle logic. No new WebView-facing capability was added; no
shell permission is exposed to the frontend at any point.

## Protocol unchanged, transport extended

The `zerorod-sidecar/v1` JSON schema (`schema`, `request_id`, `command`, `parameters`,
`result`/`error`) is byte-for-byte the same for one-shot and persistent requests — only how many
times it's exchanged over the same process differs. The sidecar's `main.py` gained a
`--persistent` CLI flag and a `run_persistent()` loop (read-request → respond → repeat until a
`shutdown` command or stdin EOF); `run_one_shot()` is untouched from TE-002 and remains the
default when `--persistent` is absent, so the original one-shot path keeps working unmodified.
