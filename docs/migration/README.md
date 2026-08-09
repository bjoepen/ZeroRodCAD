# ZeroRodCAD Desktop 2.0 — Migration Overview

This document is the entry point for the migration from ZeroRodCAD's current PySide6/Qt desktop
application to the accepted Tauri v2 based target architecture. It links the completed research to
the upcoming build sequence and states the current status plainly. It does not itself authorize or
contain implementation work — the concrete next step is
[`BUILD-022-TAURI-DESKTOP-FOUNDATION.md`](BUILD-022-TAURI-DESKTOP-FOUNDATION.md), and even that
document is a preparation document, not an implementation order.

## Current status

```text
RESEARCH COMPLETE
ARCHITECTURE ACCEPTED
MIGRATION PREPARED
BUILD 022 IN PROGRESS
  M1 — Tauri Desktop Foundation:       COMPLETE
  M2 — Productive Sidecar & Lifecycle: COMPLETE
  M3 — Three.js Preview Foundation:    PARTIAL (engineering COMPLETE, human validation PENDING)
  M4 — Productive Packaging Baseline:  NEXT (after M3 human validation)
```

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
- **Migration:** PREPARED (this document, `BUILD-022-TAURI-DESKTOP-FOUNDATION.md`, updated
  `README.md`/`ROADMAP.md`).
- **Build 022:** IN PROGRESS.
  - M1 — Tauri Desktop Foundation: COMPLETE (`BUILD-022-M1-TAURI-FOUNDATION.md`) — productive
    `desktop/` Tauri v2 shell, working WebView↔Rust IPC bridge, security boundary in place.
  - M2 — Productive Sidecar & Rust Lifecycle: COMPLETE / Gate PASS (`BUILD-022-M2-SIDECAR-LIFECYCLE.md`) —
    persistent onedir Python sidecar, Rust engine manager (lazy start, timeout, crash detection +
    restart-once, graceful shutdown), 79 new Rust/Python/frontend tests, real bundled-binary
    validation including a real crash simulation, and human validation PASS (Project Owner,
    2026-08-09, `BUILD-022-M2-HUMAN-VALIDATION.md`).
  - M3 — Three.js Preview Foundation: engineering COMPLETE / Gate PASS (`BUILD-022-M3-THREEJS-PREVIEW.md`) —
    real `zerorod-mesh/v1` payload rendered via Three.js (body/rod meshes, virtual-string lines),
    `OrbitControls` rotate/zoom, bounds-based camera fit, resize, refresh without stale geometry,
    disposal, 53 frontend tests (up from M2's 17), one new read-only Rust command
    (`engine_preview_mesh`). Human validation PENDING (`BUILD-022-M3-HUMAN-VALIDATION.md`) — same
    environment limitation every milestone in this series hit; overall M3 status PARTIAL until
    closed.
