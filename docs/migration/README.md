# ZeroRodCAD Desktop 2.0 — Migration Overview

This document is the entry point for the migration from ZeroRodCAD's current PySide6/Qt desktop
application to the accepted Tauri v2 based target architecture. It links the completed research to
the build sequence that established the productive Desktop 2.0 foundation (Build 022) and its
parameter-editing/live-preview capability (Build 023), and states the current status plainly.
Build 022's own completion record is [`BUILD-022-COMPLETION.md`](BUILD-022-COMPLETION.md); Build
023's is [`BUILD-023-COMPLETION.md`](BUILD-023-COMPLETION.md); the next build's handoff is
[`BUILD-024-HANDOFF.md`](BUILD-024-HANDOFF.md).

## Current status

```text
RESEARCH COMPLETE
ARCHITECTURE ACCEPTED
BUILD 022 COMPLETE
  M1 — Tauri Desktop Foundation:       COMPLETE
  M2 — Productive Sidecar & Lifecycle: COMPLETE
  M3 — Three.js Preview Foundation:    COMPLETE
  M4 — Productive Packaging Baseline:  COMPLETE
  M5 — Integration & Build Completion: COMPLETE
DESKTOP 2.0 FOUNDATION: ESTABLISHED
BUILD 023 COMPLETE
  M1 — Parameter Model & Request Contract Foundation: COMPLETE — Gate BUILD-023-M1: PASS
  M2 — Parameter Controls Foundation:                 COMPLETE — Gate BUILD-023-M2: PASS, Human PASS
  M3 — Parameter-to-Engine Integration:                COMPLETE — Gate BUILD-023-M3: PASS, Human PASS
  M4 — Live Preview Behavior & UX:                     COMPLETE — Gate BUILD-023-M4: PASS, Human PASS
  M5 — Integration & Build Completion:                 COMPLETE — Gate BUILD-023: PASS
PARAMETERS & LIVE PREVIEW: ESTABLISHED
BUILD 024 — STL / STEP EXPORT WORKFLOW: IN PROGRESS
  M1 — Export Architecture & Contract Foundation: COMPLETE — Gate BUILD-024-M1: PASS
  M2 — Native Save Dialog & Export Controls:      engineering COMPLETE — Gate BUILD-024-M2: PASS,
                                                   Human Validation PENDING
NEXT: BUILD 024 / M2 HUMAN VALIDATION, then BUILD 024 / M3 (requires Project Owner approval)
```

**Desktop 2.0 Foundation established** (Build 022) means the new architecture is real, tested, and
reproducibly packaged. **Parameters & Live Preview established** (Build 023) means parameter editing
and real, engine-driven live regeneration are now real, tested, and productive too — not that the
full migration from the existing PySide6 application is complete. Build 024 M1 (COMPLETE) exposed
the existing `export_project` engine capability through a tested, dedicated sidecar/Rust command
boundary and a narrow native-dialog security delta. Build 024 M2 (engineering COMPLETE) wires that
boundary into a real "Export Model…" UI trigger, a backend-driven overwrite-conflict preflight, and
a small isolated export state machine — Human Validation of the fresh release build is PENDING. Full
feature parity remains explicitly Build 025–026 scope, not yet built. See
[`BUILD-024-M1-EXPORT-FOUNDATION.md`](BUILD-024-M1-EXPORT-FOUNDATION.md) and
[`BUILD-024-M2-EXPORT-CONTROLS.md`](BUILD-024-M2-EXPORT-CONTROLS.md) for the full record.

## Why migrate

The existing PySide6/Qt desktop app bundles VTK, which none of ZeroRodCAD's actual CAD workflows
(geometry, tessellation, preview, STL export, STEP export) require. VTK alone accounts for 584.10
MiB of a 910.51 MiB historical bundle. A sequence of Technology Evaluations set out to answer,
with reproducible evidence rather than assumption, whether that dependency could be removed and
whether a modern desktop-shell + preview stack could replace PySide6/Qt + VTK without rewriting the
CAD engine itself. Both questions now have evidence-backed, project-owner-approved answers.

## Evidence summary

| Evaluation | Result | Gate |
|---|---|---|
| TE-001 — No-VTK feasibility | FAIL for unmodified CadQuery (eager `vtkmodules` import) | — |
| TE-001.1 — CadQuery No-VTK import decoupling | PASS — small, mechanical, reversible patch | — |
| TE-001.2 — No-VTK production bundle proof | Gate C PASS, HIGH confidence — 910.51 → 380.12 MiB (−58.25%) | Gate C |
| TE-002 — Tauri v2 + Python sidecar + Three.js | Gate D PASS, MEDIUM confidence — full data chain proven | Gate D |
| TE-002.1 — Sidecar runtime strategy | Gate E-A PASS — persistent + onedir, ~0.644 s cold start | Gate E-A |
| TE-002.2A — Bundle composition discovery | Gate F-A PASS — 98.15% of 673.34 MiB bundle is sidecar payload | Gate F-A |
| TE-002.2B — Targeted bundle optimization | Gate F-B PASS — 293,892,882 bytes / ~280.27 MiB (−58.37%), no regression | Gate F-B |
| TE-002.2B Human Validation | **PASS within implemented PoC scope** (2026-08-09) — app starts, model renders and is interactive; parameter editing explicitly NOT IMPLEMENTED / NOT TESTABLE, not a failure | Gate E-B / F-B human leg |

Full detail: `docs/research/TE-001-No-VTK/` through `docs/research/TE-002.2B-Tauri-Bundle-Optimization/`.
Formal decision: [`docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`](../adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md)
(Status: Accepted, 2026-08-09).

## Approved architecture

```text
ZeroRodCAD Desktop 2.0
    │
    ├── Tauri v2
    │     ├── native Desktop Shell
    │     ├── WebView UI
    │     └── Three.js 3D Preview
    │
    ├── Rust Process / IPC Layer
    │
    └── Persistent Python 3.13 Sidecar (PyInstaller onedir)
          ├── ZeroRodCAD Engine (unchanged)
          ├── CadQuery + cadquery-ocp-novtk
          ├── Geometry / Tessellation / PreviewMesh
          ├── STL
          └── STEP
```

Contracts carried over unchanged from the experiments: `zerorod-sidecar/v1` (private stdin/stdout
JSON protocol) and `zerorod-mesh/v1` (renderer-agnostic mesh transport). Packaging baseline:
persistent onedir, no onefile fallback, deduplicated OpenCASCADE dylibs, `numba`/`llvmlite`/`scipy`
excluded, no VTK, no PySide6/Qt in the Tauri runtime. Full rationale in the ADR.

## Migration principles

- **The proven PoC is not the product.** `experiments/te002-tauri/` stays research evidence,
  regression reference, and historical proof. Build 022 carries the *proven principles* into a
  controlled, productive ZeroRodCAD project structure — it does not simply relabel the experiment.
- **The CAD engine is not touched.** The migration is a desktop-shell, process-boundary, preview-
  transport, UI, and packaging change. No CAD-algorithm redesign, no new CAD kernel, no geometry
  reimplementation in Rust or TypeScript.
- **Contracts are stable by default.** `zerorod-sidecar/v1` and `zerorod-mesh/v1` are adopted as-is
  for Build 022. No protocol reinvention without a concretely demonstrated product need.
- **The TE-002.2B packaging baseline (~280.27 MiB) is a reference, not a hard limit.** Real product
  features will move it. Every significant packaging or performance change must be measured against
  it, not assumed safe.
- **The security boundary does not move.** WebView: no shell/process/broad filesystem permission.
  Rust: owns sidecar lifecycle, IPC, timeout, cleanup. IPC: private stdin/stdout. CSP: restrictive.
  See the ADR's "Security boundary" section.
- **Standard engineering discipline continues.** Versioned documentation, ADRs/ECRs where
  applicable, Definition of Done, validation evidence, before/after evidence, Git workflow — no
  special exemption just because the GUI technology is changing.

## Build sequence (022–026)

| Build | Goal | Explicitly not in scope |
|---|---|---|
| **022 — Tauri Desktop Foundation** | Productive Tauri v2 shell, Rust process/IPC layer, persistent onedir sidecar, existing engine integration, `zerorod-sidecar/v1`/`zerorod-mesh/v1`, No-VTK + TE-002.2B packaging baseline, diagnostics, tests | Complete parameter UI, complete export UI, full feature parity, PySide6 removal |
| **023 — Parameters & Live Preview** | Full `ZeroRodParameters` UI, validation, live regeneration, responsive preview, error presentation | Export workflow, settings, PySide6 removal |
| **024 — STL / STEP Export Workflow** | Productive STL/STEP export, native dialogs, export status/error handling, regression comparison with the PySide6 reference | Full feature parity, PySide6 removal |
| **025 — Desktop Feature Parity** | Remaining workflows, settings, project open/save, shortcuts, desktop integration, accessibility | Production packaging/signing, PySide6 removal |
| **026 — Production Packaging & macOS Integration** | Production bundle, final dependency audit, performance baseline, signing/notarization *preparation* | Actually signing/notarizing as a new subproject, PySide6 removal |
| **Post-026 — PySide6 Retirement Decision** | Explicit decision to retain or remove the legacy PySide6 desktop path | Happens only after feature parity, real-world validation, and a rollback archive exist |

Detailed preparation for the next build only: [`BUILD-022-TAURI-DESKTOP-FOUNDATION.md`](BUILD-022-TAURI-DESKTOP-FOUNDATION.md).
Builds 023–026 are planned at the level of this table; each gets its own preparation document when
it becomes the active build.

## Reference implementation policy

- `experiments/te002-tauri/` (the PoC) is retained, not deleted, as research evidence and a
  regression reference for Build 022's own testing.
- The existing PySide6/Qt desktop application is retained, not deleted, as the functional
  reference, feature-parity baseline, and rollback path until an explicit, separate retirement
  decision is made (see "Build sequence" table, Post-026).
- Neither is cleaned up or removed as a side effect of any migration Build; removal is always its
  own explicit decision.

## Rollback policy

No irreversible step is taken by adopting this architecture. The PySide6 application is untouched
by every TE and remains fully functional throughout the migration. Within the productive Tauri
codebase, Build 022 is expected to preserve the same "don't delete a working fallback casually"
discipline the PoC itself followed (e.g. keeping the one-shot sidecar path available alongside the
persistent default during TE-002.1). If a migration Build needs to be rolled back, the previous
Build's tag/branch and the PySide6 app remain the two concrete rollback anchors.

## Current status detail

- **Research phase:** COMPLETE (TE-001 through TE-002.2B, including human validation).
- **Architecture decision:** ACCEPTED (`docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`).
- **Build 022:** COMPLETE. Desktop 2.0 Foundation: ESTABLISHED.
  - M1 — Tauri Desktop Foundation: COMPLETE (`BUILD-022-M1-TAURI-FOUNDATION.md`) — productive
    `desktop/` Tauri v2 shell, working WebView↔Rust IPC bridge, security boundary in place.
  - M2 — Productive Sidecar & Rust Lifecycle: COMPLETE / Gate PASS (`BUILD-022-M2-SIDECAR-LIFECYCLE.md`) —
    persistent onedir Python sidecar, Rust engine manager (lazy start, timeout, crash detection +
    restart-once, graceful shutdown), 79 new Rust/Python/frontend tests, real bundled-binary
    validation including a real crash simulation, and human validation PASS (Project Owner,
    2026-08-09, `BUILD-022-M2-HUMAN-VALIDATION.md`).
  - M3 — Three.js Preview Foundation: COMPLETE / Gate PASS (`BUILD-022-M3-THREEJS-PREVIEW.md`) —
    real `zerorod-mesh/v1` payload rendered via Three.js (body/rod meshes, virtual-string lines),
    `OrbitControls` rotate/zoom, bounds-based camera fit, resize, refresh without stale geometry,
    disposal, 53 frontend tests (up from M2's 17), one new read-only Rust command
    (`engine_preview_mesh`), and human validation PASS (Project Owner, 2026-08-09,
    `BUILD-022-M3-HUMAN-VALIDATION.md`).
  - M4 — Productive Packaging Baseline: COMPLETE / Gate PASS
    (`BUILD-022-M4-PRODUCTIVE-PACKAGING.md`) — productive dylib deduplication
    (`packaging/tauri/dedup_bundle_dylibs.py`, hash-gated, symlink-safety-verified, idempotent),
    reproducible build pipeline (`scripts/build-productive-desktop-app.sh`), release build measured
    at 285.21 MiB (within 1.76% of TE-002.2B's own 280.27 MiB reference, fully explained), 0
    VTK/PySide6/Qt/numba/llvmlite/scipy reconfirmed, no functional/performance/security regression,
    and human validation PASS (Project Owner, 2026-08-09, `BUILD-022-M4-HUMAN-VALIDATION.md`).
  - M5 — Integration & Build Completion: COMPLETE / Gate PASS (`BUILD-022-COMPLETION.md`) —
    milestone consistency audit (no contradictions), architecture conformance audit against
    `ADR-022-001` (18 checks, 0 deviations), a byte-for-byte reproducible clean release rebuild,
    and the master validation gate (`scripts/validate-build022.sh`) ending in
    `BUILD-022 CONSISTENCY GATE: PASS`.

**Build 022 Final Gate: PASS.** See `docs/migration/BUILD-022-COMPLETION.md` for the full record
and `docs/migration/BUILD-023-HANDOFF.md` for what comes next.

- **Build 023 — Parameters & Live Preview: COMPLETE. Parameters & Live Preview: ESTABLISHED.**
  - M1 — Parameter Model & Request Contract Foundation: COMPLETE / Gate PASS
    (`BUILD-023-M1-PARAMETER-CONTRACT.md`, `BUILD-023-M1-PARAMETER-DISCOVERY.md`,
    `../contracts/ZEROROD-PARAMETERS-V1.md`) — the canonical `zerorod-parameters/v1` request
    contract, empirically derived from the existing `zerorodcad.parameters`/`zerorodcad.validation`
    domain model (no guessed/invented parameters), integrated through the Python sidecar, Rust IPC
    boundary, and a TypeScript type/contract foundation (no UI controls yet). Explicit parameter
    requests proven end to end against the real bundled sidecar: canonical-default equivalence, an
    alternate valid parameter set producing a real, attributable geometry change, structured errors
    for invalid requests, and process stability across a valid→invalid→valid sequence.
  - M2 — Parameter Controls Foundation: COMPLETE / Gate PASS (`BUILD-023-M2-PARAMETER-CONTROLS.md`)
    — a productive parameter panel covering all 16 fields (15 geometry + `project_name` metadata),
    grouped by contract-derived semantics, canonical defaults loaded through the real
    `parameters_defaults` path (never duplicated), local draft/dirty state, local structural
    validation, Reset — and human validation PASS (Project Owner).
  - M3 — Parameter-to-Engine Integration: COMPLETE / Gate PASS
    (`BUILD-023-M3-PARAMETER-ENGINE-INTEGRATION.md`) — Apply connects the parameter draft to the
    real engine through the existing M1 contract (no protocol change, no new Rust/Python code
    needed), atomic preview replacement, a real `body_width: 38 → 60 mm` geometry change proven
    through the productive pipeline — and human validation PASS (Project Owner: "entered values
    change the real ZeroRod model as expected").
  - M4 — Live Preview Behavior & UX: COMPLETE / Gate PASS (`BUILD-023-M4-LIVE-PREVIEW.md`) —
    automatic debounced live preview (300 ms), generation-based stale-response protection, in-flight
    request coalescing, a camera-preservation heuristic so small live edits don't fight the user's
    manual framing — and human validation PASS (Project Owner).
  - M5 — Integration & Build Completion: COMPLETE / Gate PASS (`BUILD-023-COMPLETION.md`) —
    milestone consistency audit, architecture conformance re-verification against `ADR-022-001`, a
    clean final release rebuild, and the master validation gate (`scripts/validate-build023.sh`)
    ending in `BUILD-023 CONSISTENCY GATE: PASS`.

**Build 023 Final Gate: PASS.** See `docs/migration/BUILD-023-COMPLETION.md` for the full record and
`docs/migration/BUILD-024-HANDOFF.md` for the Build 024 handoff.

- **Build 024 — STL / STEP Export Workflow: IN PROGRESS.**
  - M1 — Export Architecture & Contract Foundation: COMPLETE / Gate PASS
    (`BUILD-024-M1-EXPORT-FOUNDATION.md`) — the existing, unmodified
    `zerorodcad.export.export_project` exposed through a dedicated sidecar `export` command and a
    dedicated Rust `engine_export` command; canonical export-source semantics decided (the
    frontend's `accepted` state); real default and alternate-parameter export proven end to end
    against a real persistent sidecar process; a discovered CadQuery silent-failure mode on
    unwritable directories addressed with sidecar-side post-export verification; silent
    overwrite-in-place established; a narrow native-dialog security delta (`dialog:allow-open`
    only, no filesystem permission granted to the WebView); export timing measured safe against
    the existing 30 s timeout; no export UI yet — that is M2's scope.
  - M2 — Native Save Dialog & Export Controls: engineering COMPLETE / Gate BUILD-024-M2: PASS
    (`BUILD-024-M2-EXPORT-CONTROLS.md`) — a real "Export Model…" trigger sourcing the accepted
    parameter state, the M1 native directory dialog wired in, a new backend-driven
    overwrite-conflict preflight (sidecar `export_preflight` + Rust `engine_export_preflight`,
    reusing the engine's own filename sanitization rather than duplicating it), an in-panel
    overwrite confirmation (no new dialog capability — `dialog:allow-open` remains the only
    delta from Build 023), and an isolated `export_panel.ts` state machine that stays disabled
    while live preview is pending so "Export" always means the model on screen; real end-to-end
    proof (preview → preflight → export → preflight-detects-conflict → export-overwrites →
    preview → shutdown) against the real persistent sidecar; fresh release `.app` built and
    measured (285.9 MiB, +0.6 MiB vs. the Build 022/023 baseline, fully explained by the dialog
    plugin's native macOS bindings). Human Validation **PENDING**
    (`BUILD-024-M2-HUMAN-VALIDATION.md`).

**Next: Build 024 / M2 Human Validation**, then **Build 024 / M3** (requires explicit Project
Owner approval to start, per the mandate's stop condition after M2).
