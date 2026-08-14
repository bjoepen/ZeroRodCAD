# ZeroRodCAD Roadmap

## Leitlinie

Die Roadmap wird evidenzbasiert entwickelt.

Technologieentscheidungen werden nicht allein nach Plausibilität oder Bundlegröße getroffen, sondern über reproduzierbare Technology Evaluations, Messungen und klar definierte Gates abgesichert.

---

## Completed Research

### Foundations

- [x] Build 010 – Desktop foundation
- [x] Build 011 – Interactive workspace
- [x] Build 012 – macOS application foundation
- [x] Build 013 – Packaging diagnostics
- [x] Build 014 – Preview recovery
- [x] Build 015 – Lean runtime audit

### Analysis & Architecture Tooling

- [x] Build 019.x – Scanner 2.0 / Bundle analysis foundation
- [x] Build 019.3 – Dead-library, dependency and optimization analysis
- [x] Build 020 M1 – Analysis core extraction
- [x] Build 020 M2 – Analysis pipeline architecture
- [x] Build 020 M3 – Unified report engine
- [x] Build 020 M4 – Performance, benchmark and Build-020 stabilization
- [x] Build 021 M1 – Read-only Runtime Trace foundation

Build 021 M2–M4 were intentionally paused when the No-VTK/Tauri architecture question became the higher-value investigation.

### Technology Evaluation Phase — COMPLETE

TE-001 through TE-002.2B are formally complete. No TE-002.3 is planned; further open product
questions (full parameter UI, export UI, feature parity) belong in the migration builds below, not
in another foundational Technology Evaluation, unless a genuinely new architectural uncertainty
emerges.

#### TE-001 – No-VTK Feasibility

- [x] Isolated Python 3.13 environment
- [x] cadquery-ocp-novtk evaluation
- [x] VTK import blocker
- [x] Runtime and OS-level evidence
- [x] IVtk boundary test
- [x] Root cause identified

**Result:** FAIL for unmodified CadQuery 2.8.0 because CadQuery eagerly imports `vtkmodules`.

#### TE-001.1 – CadQuery No-VTK Import Decoupling

- [x] Minimal CadQuery patch
- [x] `import cadquery` without VTK
- [x] Geometry
- [x] Tessellation
- [x] PreviewMesh
- [x] STL
- [x] STEP
- [x] VTK-specific functions fail cleanly
- [x] Backward compatibility with full VTK stack
- [x] Regression tests

**Result:** PASS

#### TE-001.2 – No-VTK Production Bundle Proof

- [x] Real macOS PyInstaller bundle
- [x] App startup
- [x] Preview contract
- [x] STL
- [x] STEP
- [x] Static VTK = 0
- [x] Runtime VTK = 0
- [x] OS-level VTK = 0
- [x] Real-world user test
- [x] Bundle-size comparison

**Result:** Gate C PASS / HIGH confidence

Measured reduction:

```text
910.51 MiB → 380.12 MiB
−530.39 MiB
−58.25 %
```

#### TE-002 – Tauri v2 + Three.js Preview Architecture

- [x] Tauri v2 shell
- [x] Rust-owned sidecar lifecycle
- [x] Python 3.13 sidecar
- [x] No-VTK CadQuery path
- [x] `zerorod-sidecar/v1`
- [x] `zerorod-mesh/v1`
- [x] PreviewMesh transport
- [x] Three.js BufferGeometry conversion
- [x] Error handling
- [x] Security boundary
- [x] Automated Python/Rust/frontend tests
- [x] Performance measurements

**Result:** Gate D PASS / MEDIUM confidence

Open findings carried into TE-002.1: PyInstaller onefile sidecar cold start too slow (~15 s);
human interactive rendering confirmation still required.

#### TE-002.1 – Sidecar Runtime Strategy & Human Validation

Variants compared:

- [x] A – onefile / one-shot baseline
- [x] B – onedir / one-shot
- [x] C – persistent sidecar
- [x] D – persistent + onedir

Engineering topics:

- [x] Cold-start benchmark
- [x] Warm-request benchmark
- [x] Memory behavior
- [x] Process cleanup
- [x] Crash recovery
- [x] App-close cleanup
- [x] No-VTK regression
- [x] No-PySide regression
- [x] Test `.app` build
- [x] Runtime strategy recommendation

**Result:** Gate E-A PASS (engineering), MEDIUM confidence. Recommendation: **persistent + onedir**
— cold start ~0.644 s vs. ~15–17 s for onefile; no structural orphan-process risk under forced kill
(onefile has this risk, onedir does not).

#### TE-002.2A – Tauri Bundle Composition Discovery

- [x] Full bundle size measurement (706,051,017 bytes / 673.34 MiB / 372 files)
- [x] Sidecar share isolated (660.93 MiB / 98.15 %)
- [x] Tauri/Rust/frontend share isolated (13.04 MiB)
- [x] VTK = 0 confirmed (three independent methods)
- [x] PySide6/Qt = 0 confirmed (two independent methods)
- [x] Duplicate-file investigation (hash-based, 93.90 MiB)
- [x] Optimization candidates identified (5, with evidence status)
- [x] No optimization performed (discovery only)

**Result:** Gate F-A PASS

#### TE-002.2B – Targeted Bundle Optimization

- [x] Candidate A — remove onefile fallback (−135.45 MiB)
- [x] Candidate B — restore PyInstaller dylib symlink dedup after Tauri's resource copy (−93.90 MiB)
- [x] Candidate C — exclude numba/llvmlite (−128.27 MiB)
- [x] Candidate D — exclude scipy (−35.45 MiB)
- [x] Root-cause investigation per candidate (not "not observed" alone)
- [x] Real rebuilds, not hand-edited artifacts
- [x] Full regression suite (48/48 sidecar, 241/1-skip full repo, 17/17 Rust, 30/30 frontend)
- [x] Performance/memory benchmark — no regression
- [x] Functional validation (launch, preview, STL, STEP, repeated requests, error handling, shutdown, 0 orphan processes)

**Result:** Gate F-B PASS. Final optimized bundle:

```text
293,892,882 bytes / ~280.27 MiB / 193 files
−393.07 MiB / −58.37 % vs. the 673.34 MiB TE-002.1 baseline
```

Performance: cold start ~0.612 s, warm median ~0.121 s — no regression vs. TE-002.1's own
persistent+onedir numbers.

**Human Validation (Project Owner, 2026-08-09):** **PASS within implemented PoC scope.** App
starts for real; the ZeroRod model and its existing parts (body, rod, virtual strings) render
correctly; rotate and zoom work; existing preview interaction works. Parameter editing is
explicitly **NOT IMPLEMENTED / NOT TESTABLE** in the PoC UI — a scope gap, not a failure. Full
record: `docs/research/TE-002.2B-Tauri-Bundle-Optimization/HUMAN-VALIDATION.md`.

---

## Architecture Decision — ACCEPTED

**Status: ACCEPTED, 2026-08-09.** Full decision record:
[`docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`](docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md).

### ZeroRodCAD Desktop 2.0 — Approved Target Architecture

```text
Tauri v2 GUI
    +
Rust process / IPC layer
    +
Persistent Python 3.13 Engine Sidecar (PyInstaller onedir)
    +
CadQuery + cadquery-ocp-novtk
    +
PreviewMesh / JSON contracts (zerorod-sidecar/v1, zerorod-mesh/v1)
    +
Three.js
```

Completed before productive migration:

- [x] finalize ADR (`ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`, Status: Accepted)
- [x] define CadQuery patch deployment strategy (upstream preferred, version-pinned local patch as
  interim, no permanent fork)
- [x] define migration milestones (Build 022–026, below)
- [x] retain PySide6 app as rollback/reference until feature parity — codified in the ADR and in
  `docs/migration/README.md`'s reference-implementation policy

---

## ZeroRodCAD Desktop 2.0 Migration

Migration overview: [`docs/migration/README.md`](docs/migration/README.md).
Current status:

```text
RESEARCH COMPLETE
ARCHITECTURE ACCEPTED
MIGRATION PREPARED
BUILD 022 COMPLETE (M1 COMPLETE, M2 COMPLETE, M3 COMPLETE, M4 COMPLETE, M5 COMPLETE)
DESKTOP 2.0 FOUNDATION ESTABLISHED
BUILD 023 COMPLETE (M1 COMPLETE, M2 COMPLETE, M3 COMPLETE, M4 COMPLETE, M5 COMPLETE)
PARAMETERS & LIVE PREVIEW ESTABLISHED
BUILD 024 COMPLETE (M1 COMPLETE, M2 COMPLETE — Human PASS, M3 COMPLETE — Human PASS,
  M4 COMPLETE — Integration & Build Completion)
STL / STEP EXPORT WORKFLOW ESTABLISHED
BUILD 025 IN PROGRESS (Discovery COMPLETE — Gate PASS, M1 COMPLETE — Gate BUILD-025-M1: PASS,
  Human Validation PASS, M2 COMPLETE — Gate BUILD-025-M2: PASS, Human Validation PASS,
  M3 COMPLETE — Gate BUILD-025-M3: PASS, Human Validation PASS,
  M4 COMPLETE — Gate BUILD-025-M4: PASS, Human Validation PASS,
  M5 IN PROGRESS — Integration, Completion & Repository Cleanup)
NEXT: BUILD 025 / M5 INTEGRATION & COMPLETION
```

### Current

Build 022 is **complete**. M1 (Tauri Desktop Foundation), M2 (Productive Sidecar & Rust
Lifecycle), M3 (Three.js Preview Foundation), M4 (Productive Packaging Baseline), and M5
(Integration & Build Completion) are all complete, each with Gate PASS including human validation
where applicable. The productive Desktop 2.0 foundation (Tauri v2 + Rust process layer +
persistent Python sidecar + Three.js preview) is established, tested, and reproducibly packaged.
This is the desktop **foundation**, not a completed feature migration — see
[`docs/migration/BUILD-022-COMPLETION.md`](docs/migration/BUILD-022-COMPLETION.md) for the full
completion record and [`docs/migration/BUILD-023-HANDOFF.md`](docs/migration/BUILD-023-HANDOFF.md)
for what Build 023 picks up next.

### Build 022 – Tauri Desktop Foundation

Preparation document: [`docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md`](docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md).

- [x] M1 — productive Tauri v2 application shell (`docs/migration/BUILD-022-M1-TAURI-FOUNDATION.md`)
- [x] M2 — Rust-owned sidecar process lifecycle (spawn, reuse, timeout, crash/restart, shutdown) — `docs/migration/BUILD-022-M2-SIDECAR-LIFECYCLE.md`
- [x] M2 — persistent, onedir-packaged Python 3.13 sidecar (`src/zerorod_sidecar/`, `packaging/tauri/sidecar-onedir.spec`)
- [x] M2 — existing ZeroRodCAD engine integration (unchanged)
- [x] M2 — `zerorod-sidecar/v1` adopted stable
- [x] M2 — `zerorod-mesh/v1` received and validated (not yet rendered)
- [x] M3 — Three.js preview foundation — `docs/migration/BUILD-022-M3-THREEJS-PREVIEW.md`; body/rod meshes + virtual-string lines rendered, OrbitControls, camera fit, resize, refresh/dispose
- [x] M1 — No-VTK-clean shell (no Python/sidecar dependency yet to violate it)
- [x] M2 — No-VTK sidecar packaging with the TE-002.2B optimized packaging rules as baseline (full app-bundle dylib dedup remains M4's scope — see "Packaging note" in `BUILD-022-M2-SIDECAR-LIFECYCLE.md`)
- [x] M3 — No-VTK/No-PySide6 reconfirmed unchanged (M3 touched no Python code)
- [x] M2 — diagnostics (`engine_status`/`engine_sidecar_status`, structured `EngineError` throughout)
- [x] M1/M2/M3 — tests (21 Rust, 41 Python, 53 frontend as of M3; full repo regression 282 passed/1 skipped)
- [x] M1/M2/M3 — real app validation pass (launch, IPC bridge, real bundled-binary protocol round trip incl. a real crash simulation, real payload through the real mesh converter, clean shutdown, 0 orphan processes)
- [x] M2 — human validation PASS (Project Owner, 2026-08-09, `BUILD-022-M2-HUMAN-VALIDATION.md`) — Gate BUILD-022-M2: PASS
- [x] M3 — human validation PASS (Project Owner, 2026-08-09, `docs/migration/BUILD-022-M3-HUMAN-VALIDATION.md`) — Gate BUILD-022-M3: PASS
- [x] M4 — productive dylib deduplication (`packaging/tauri/dedup_bundle_dylibs.py`, hash-gated, symlink-safety-verified, idempotent) — `docs/migration/BUILD-022-M4-PRODUCTIVE-PACKAGING.md`
- [x] M4 — reproducible build pipeline (`scripts/build-productive-desktop-app.sh`)
- [x] M4 — release build measured: 285.21 MiB, within 1.76% of TE-002.2B's 280.27 MiB reference, fully explained (Size Classification A)
- [x] M4 — No-VTK/No-PySide6/no-onefile/no-numba/no-llvmlite/no-scipy reconfirmed in the final bundle
- [x] M4 — functional/lifecycle/performance/memory/security regression against the exact final bundle, no regression
- [x] M4 — human validation PASS (Project Owner, 2026-08-09, `docs/migration/BUILD-022-M4-HUMAN-VALIDATION.md`) — Gate BUILD-022-M4: PASS
- [x] M5 — milestone consistency audit (M1-M4 claims vs. repository, no contradictions found) — `docs/migration/BUILD-022-COMPLETION.md`
- [x] M5 — architecture conformance audit vs. `ADR-022-001` (18 checks, 0 deviations)
- [x] M5 — clean release rebuild from scratch: byte-for-byte reproducible (299,066,193 bytes / 285.21 MiB / 201 files / 77 symlinks, identical to M4's own measurement)
- [x] M5 — master validation gate (`scripts/validate-build022.sh`) — orchestrates M2/M3/M4 gates + architecture conformance + final inventory — `BUILD-022 CONSISTENCY GATE: PASS`
- [x] M5 — Build 023 handoff prepared, not started (`docs/migration/BUILD-023-HANDOFF.md`)

**Build 022: COMPLETE. Desktop 2.0 Foundation: ESTABLISHED.**

Not yet in Build 022 (by design — later builds' scope): complete parameter UI, complete export UI,
full feature parity, PySide6 removal, signing/notarization.

### Build 023 – Parameters & Live Preview

- [x] M1 — Parameter Model & Request Contract Foundation — `docs/migration/BUILD-023-M1-PARAMETER-CONTRACT.md`, `docs/migration/BUILD-023-M1-PARAMETER-DISCOVERY.md`, `docs/contracts/ZEROROD-PARAMETERS-V1.md` — `zerorod-parameters/v1` request contract defined, engine-owned parameter/validation model confirmed as the single source of truth, Python/Rust/TypeScript boundaries integrated, real explicit-parameter requests proven end to end against the bundled sidecar (canonical-default equivalence, alternate-parameter geometry change, structured invalid-parameter errors, valid-after-invalid process stability), no UI added — Gate BUILD-023-M1: PASS
- [x] M2 — Parameter Controls Foundation — `docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md` — productive parameter panel covering all 16 `zerorod-parameters/v1` fields (15 geometry + `project_name` metadata), grouped by contract-derived semantics, canonical defaults loaded through the real `parameters_defaults` path (never duplicated), local draft/dirty state, local structural validation, Reset — Gate BUILD-023-M2: PASS, Human Validation PASS (Project Owner)
- [x] M3 — Parameter-to-Engine Integration — `docs/migration/BUILD-023-M3-PARAMETER-ENGINE-INTEGRATION.md` — Apply connects the parameter draft to the real engine through the existing `zerorod-parameters/v1`/`zerorod-sidecar/v1` path (no protocol change, no new Rust/Python code needed — M1 had already built it), atomic preview replacement, an accepted-state model, a metadata-only-Apply optimization, a real `body_width: 38 → 60 mm` geometry change proven through the productive pipeline — Gate BUILD-023-M3: PASS, Human Validation PASS (Project Owner)
- [x] M4 — Live Preview Behavior & UX — `docs/migration/BUILD-023-M4-LIVE-PREVIEW.md` — automatic debounced live preview (300 ms, chosen from the measured ~0.12 s warm engine round trip), generation-based stale-response protection, in-flight request coalescing, a camera-preservation heuristic (refit only on first load / an extreme bounds change) so small live edits don't fight the user's manual framing, Apply/Reset unified with the live-preview pipeline — Gate BUILD-023-M4: PASS, Human Validation PASS (Project Owner)
- [x] M5 — Integration & Build Completion — `docs/migration/BUILD-023-COMPLETION.md` — milestone consistency audit (no contradictions found), architecture conformance re-verification against `ADR-022-001`, a clean final release rebuild, and the master validation gate (`scripts/validate-build023.sh`) ending in `BUILD-023 CONSISTENCY GATE: PASS`

**Build 023: COMPLETE. Parameters & Live Preview: ESTABLISHED.**

Not yet in Build 023 (by design — later builds' scope): STL/STEP export UI, full feature parity,
project persistence, PySide6 removal, signing/notarization.

### Build 024 – STL / STEP Export Workflow

Handoff document: [`docs/migration/BUILD-024-HANDOFF.md`](docs/migration/BUILD-024-HANDOFF.md).

- [x] M1 — Export Architecture & Contract Foundation — `docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md` — the existing, unmodified `zerorodcad.export.export_project` exposed through a dedicated sidecar `export` command and a dedicated Rust `engine_export` command (same "new command, not an overloaded flag" pattern as `engine_preview_mesh_with_parameters`); canonical export-source semantics decided (the frontend's `accepted` state, not the draft); real default and alternate-parameter export proven end to end against a real persistent sidecar process; empirical discovery that CadQuery's STL/STEP exporters can silently no-op on an unwritable directory, addressed with a post-export file-existence/non-empty verification step in the sidecar boundary (`export_incomplete`); silent-overwrite-in-place behavior established; a new, narrow native-dialog security-boundary delta (`tauri-plugin-dialog`, `dialog:allow-open` only, no filesystem permission granted to the WebView); STL/STEP export timing measured (~0.13 s warm, ~1.45 s cold) against the existing 30 s timeout — classified SAFE, retained unchanged; no export UI yet — Gate BUILD-024-M1: PASS
- [x] M2 — Native Save Dialog & Export Controls — `docs/migration/BUILD-024-M2-EXPORT-CONTROLS.md` — a real "Export Model…" trigger (near Apply, sourcing the frontend's `accepted` state, never the draft), the M1 native directory dialog wired in, a new backend-driven overwrite-conflict preflight (sidecar `export_preflight` + Rust `engine_export_preflight`, reusing `zerorodcad.export.expected_output_filenames` rather than duplicating the sanitization), an in-panel overwrite confirmation (no new dialog capability — `dialog:allow-open` remains the only WebView delta since Build 023), and an isolated `export_panel.ts` export state machine (idle → selecting_destination → checking_destination → exporting/confirm_overwrite → success/error) disabled while live preview is pending/updating; real end-to-end proof against the persistent sidecar (preview → preflight → export → preflight-detects-conflict → export-overwrites → preview → shutdown); fresh release `.app` built and measured (285.9 MiB) — Gate BUILD-024-M2: PASS; Round 1 Human Validation found a real `outputDirectory`/`output_directory` Tauri IPC argument-binding defect in `engine_export`/`engine_export_preflight`, fixed with `rename_all = "snake_case"` plus new real-IPC-dispatch regression tests and a validation-gate blind-spot fix (`docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md`); Round 2 Human Validation **PASS** (`docs/migration/BUILD-024-M2-HUMAN-VALIDATION.md`) — native directory selection works, export succeeds, STL/STEP/report generated, exported model opens successfully
- [x] M3 — Export Robustness & Edge Cases — `docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md` — a second, independent Rust-side structural-validation layer (`export_result.rs`) guarding against a malformed sidecar result ever reaching the frontend as success; the preflight/export TOCTOU race investigated and deliberately left unmitigated (its worst case already matches the product's accepted silent-overwrite behavior); export retry safety decided evidence-based (the existing generic retry-once-on-crash policy is safe for `export`, backed by directly-tested write idempotency, with a newly-discovered and documented STEP-internal-numbering nondeterminism that doesn't affect geometry correctness); real evidence gathered against the persistent sidecar for spaces/Unicode paths, a 20x repeated-export stress sequence, and preview/export interleaving (proving export never reflects stale geometry); zero-byte-output and simulated-disk-full error-mapping tests added; project-name empty/Unicode edge cases proven end to end; memory growth measured (+5.07% over 20 exports, tapering, no leak found) — Gate BUILD-024-M3: PASS, Human Validation **PASS** (`docs/migration/BUILD-024-M3-HUMAN-VALIDATION.md`, validated against the uniquely-named `ZeroRodCAD-Build024-M3.app`, artifact identity independently re-verified: frontend asset hash + compiled `invalid_export_result` marker both confirmed matching)
- [x] M4 — Integration & Build Completion — `docs/migration/BUILD-024-COMPLETION.md` — milestone consistency audit across M1-M3 (no contradictions), architecture/contract conformance re-verification against `ADR-022-001` (0 deviations), full test-suite re-run (347 Python + 42 Rust + 207 frontend, all green, identical to the M3 baseline — no source drift), a clean reproducible release rebuild with independent artifact-identity proof (frontend content hash, compiled marker, deterministic bundle fingerprint), and the master validation gate (`scripts/validate-build024.sh`) ending in `BUILD-024 CONSISTENCY GATE: PASS`. No new feature, no UI change, no architecture change — integration and closure only.
- [x] regression comparison with the PySide6 reference app (export field-naming/output conventions used as a non-authoritative reference throughout M1-M2; full parity validation is Build 025 scope, per the accepted build sequence)

**Build 024: COMPLETE. STL / STEP Export Workflow: ESTABLISHED.**

Not yet in Build 024 (by design — later builds' scope): project persistence, full desktop feature
parity, signing/notarization, PySide6 removal.

### Build 025 – Desktop Feature Parity

Handoff document: [`docs/migration/BUILD-025-HANDOFF.md`](docs/migration/BUILD-025-HANDOFF.md).
Discovery: [`docs/migration/BUILD-025-FEATURE-PARITY-MATRIX.md`](docs/migration/BUILD-025-FEATURE-PARITY-MATRIX.md)
and companion documents — Gate `BUILD-025 DISCOVERY GATE: PASS`.

- [x] Discovery — feature parity matrix, lifecycle/project-persistence/desktop-integration
  analyses, gap report; milestone plan (M1–M4 + Final) proposed and approved
- [x] M1 — Project Persistence — `docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md` — New/Open/
  Save/Save As against the existing, unmodified `.zerorod` format (`src/zerorodcad/project.py`);
  a new project-session model (`project_state.ts`) with `project_dirty` derived from `accepted`
  vs. the last-saved baseline (never from the draft); an uncommitted-draft check kept explicitly
  separate from `project_dirty`; a Save/Discard/Cancel unsaved-changes guard covering New, Open,
  and Quit/window-close alike; a new narrow `dialog:allow-save` WebView capability (Open reuses
  the existing `dialog:allow-open`); sidecar `project_open`/`project_save` commands and Rust
  `engine_project_open`/`engine_project_save`/`select_project_open_file`/
  `select_project_save_file` commands, each new snake_case-argument command backed by a real
  `tauri::test::get_ipc_response` IPC-binding regression test from the start. Human Validation
  found the red macOS close button non-functional — a missing `core:window:allow-destroy`
  WebView capability grant, not an application-logic defect — fixed and proven with a real
  Tauri IPC-boundary regression test (`docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md`),
  which also surfaced the (deliberately unfixed, Build 025 M4-tracked) macOS Quit/⌘Q
  guard-bypass gap — Gate BUILD-025-M1: PASS; Human Validation **PASS**
  (`docs/migration/BUILD-025-M1-HUMAN-VALIDATION.md`)
- [x] M2 — Product UI Productization & Lifecycle Polish —
  `docs/migration/BUILD-025-M2-PRODUCT-LIFECYCLE.md` — an automatic initial preview
  (`parameter_panel.ts`'s `load()`, one fetch+commit through the existing preview pipeline,
  closing the "empty viewport at first launch" gap); a startup coordinator (`startup.ts`) with an
  anti-flicker-delayed "Preparing…" indicator and a Retry/Show-Details failure surface; a new
  Diagnostics view (`diagnostics_panel.ts`) relocating the old technical Engine/Ping/raw-JSON
  controls out of the main product UI without losing them; the old 5-row status panel and four
  technical buttons removed from `main.ts`. No engine/protocol/Rust source change — Gate
  BUILD-025-M2: PASS; Human Validation **PASS** (`docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md`)
- [x] M3 — Preview & Report Parity — `docs/migration/BUILD-025-M3-PREVIEW-REPORT-PARITY.md` — a
  build-identity process correction (`app_info()` now reports `"M3"`, with a general regression
  test guarding against any earlier Build 025 milestone being reported again); Reset View —
  exactly one control, per reading legacy's `preview_widget.py` directly (no separate Fit/Reset
  pair in legacy) — via a new `boundsFromVisibleObjects` (`scene.ts`) feeding the existing,
  unchanged `fitCameraToBounds`; presentation-only Body/Rod/Strings visibility
  (`preview.ts`'s `ModelLayer`/`applyModelLayerVisibility`, the mesh contract's existing
  `"body"`/`"rod"`/`"strings"` names — no protocol change) surviving a live-preview geometry
  refresh; an in-app Instrument Report (`report.ts`/`report_panel.ts`) sourced from `accepted`
  state only, via a new additive sidecar `report` command and Rust `engine_report` command, both
  reusing `zerorodcad.report.build_report` unmodified — proven byte-for-byte identical to
  export's `report.md` for the same accepted state across three scenarios. No engine, protocol,
  or domain (`zerorodcad/`) source change — Gate BUILD-025-M3: PASS; Human Validation **PASS**
  (`docs/migration/BUILD-025-M3-HUMAN-VALIDATION.md`)
- [x] M4 — Desktop Shell & Native Integration —
  `docs/migration/BUILD-025-M4-DESKTOP-SHELL.md` — an explicit native macOS Application/File/View
  menu (`menu.rs`) replacing Tauri's implicit default, with native ⌘N/⌘O/⌘S/⇧⌘S/⌘Q accelerators;
  File/View items route to the existing `project_panel.ts`/`export_panel.ts`/`preview.ts`/
  `report_panel.ts`/`diagnostics_panel.ts` controller methods the visible UI already calls, with no
  duplicated command/decision logic in Rust. The M1-tracked Quit/⌘Q guard-bypass gap is
  **FIXED IN M4**: native Quit is a plain custom `MenuItem` (never `PredefinedMenuItem::quit`)
  whose handler calls `WebviewWindow::close()` — the identical native event pipeline the
  already-validated red close button uses (confirmed by reading `tauri-runtime-wry`'s dispatcher
  directly) — so ⌘Q now resumes through the single existing `confirmQuit()` guard, not a second
  implementation. A new `close_flow.ts` module makes overlapping close attempts (repeated ⌘Q, ⌘Q
  racing red close) resolve to exactly one guard decision, directly unit-tested. Show
  Body/Rod/Strings gained bidirectional native-menu-checkmark ↔ visible-checkbox sync via one
  shared funnel function and a narrow new `set_view_menu_checked` command (no new WebView
  capability — an app-owned, non-plugin command). `app_info()` now reports `"M4"`. No engine,
  protocol, or domain (`zerorodcad/`) source change; no new dependency — Gate BUILD-025-M4:
  PASS; Human Validation **PASS** (`docs/migration/BUILD-025-M4-HUMAN-VALIDATION.md`)
- [x] M5 — Integration, Completion & Repository Cleanup —
  `docs/migration/BUILD-025-M5-REPOSITORY-CLEANUP.md`, `docs/migration/BUILD-025-COMPLETION.md` —
  milestone consistency audit across M1-M4, a repository-wide cleanup discovery pass (0
  SAFE_TO_REMOVE code/script candidates found — the codebase stayed clean incrementally, so this
  milestone's cleanup work was documentation synchronization, not deletion), architecture
  conformance re-verification against `ADR-022-001` (0 deviations), a full test-suite re-run, a
  clean reproducible release rebuild with artifact-identity proof, and the master validation gate
  (`scripts/validate-build025.sh`) ending in `BUILD-025 CONSISTENCY GATE: PASS`

**Build 025: COMPLETE. Desktop Feature Parity: ESTABLISHED.**

Not yet in Build 025 (by design — later builds' scope): settings, Recent Files, drag & drop, file
associations/Finder integration, signing/notarization, PySide6 removal.

### Build 026 – Production Packaging & macOS Integration

- [x] production bundle — portable, checksum-pinned CPython 3.13 (`astral-sh/python-build-standalone`,
  no Homebrew dependency), corrected metadata (identifier, version, `LSRequiresCarbon`), 0
  PyInstaller hidden-import warnings
- [x] final dependency audit — VTK/PySide6/Qt/numba/llvmlite/scipy = 0; full pin-status inventory
  (`docs/migration/BUILD-026-COMPLETION.md`)
- [x] performance baseline — no regression vs. Build 022–025 (~8% bundle-size growth, fully
  explained; warm preview timing unchanged)
- [x] signing preparation — nested-component signing script (correct order, never `--deep`),
  notarization submission script, verification script; no real Developer ID credentials used
- [x] notarization preparation — `notarytool`/`stapler` workflow scripted and documented; not
  submitted
- [x] release workflow — DMG (`ZeroRodCAD-0.1.0-macOS-arm64.dmg`), release manifest, checksums,
  master gate `scripts/validate-build026.sh` (`BUILD-026 CONSISTENCY GATE: PASS`)

Signing/notarization infrastructure is prepared but not exercised with real credentials — real
Developer ID signing, notarization submission, and stapling remain an explicit, separate,
credential-gated final release step (`docs/migration/BUILD-026-RELEASE-WORKFLOW.md`), requiring
Project Owner authorization beyond this roadmap entry. Full record:
[`docs/migration/BUILD-026-COMPLETION.md`](docs/migration/BUILD-026-COMPLETION.md).

**Build 026: FINALIZATION ENGINEERING COMPLETE. Human Validation of the Release Candidate PENDING.**

### Post-Build-026 – PySide6 Retirement Decision

Only after:

- [ ] feature parity confirmed
- [ ] real-world testing complete
- [ ] rollback package archived
- [ ] final architecture review

Decision: retain or remove the legacy PySide6 desktop path.

---

## Later

- [ ] Apple signing and notarization
- [ ] Universal macOS release, if still required and justified
- [ ] upstream CadQuery No-VTK contribution
- [ ] CI coverage for No-VTK production packaging
- [ ] performance regression thresholds after stable baseline exists
- [ ] refine bundle/dependency analyzer confidence before using removal recommendations automatically

---

## Explicitly Not Planned Yet

- no deletion of the existing PySide6 application (only after the Post-Build-026 retirement decision)
- no deletion of `experiments/te002-tauri/` (remains research evidence and regression reference)
- no binary mesh protocol without evidence
- no new CAD kernel
- no separate repository for the Tauri experiment or the productive Tauri app
- no full UI redesign inside Technology Evaluations (phase is complete; UI work now belongs to Build 023/025)
- no further Technology Evaluation (TE-002.3) unless a genuinely new architectural uncertainty emerges

---

## Decision Principle

The current project direction is no longer:

> Make the existing bundle smaller at any cost.

It is now:

> Preserve the proven ZeroRodCAD engine, minimize unnecessary runtime dependencies, and execute the accepted Tauri v2 desktop architecture through a measured, testable, reversible migration — starting with Build 022.
