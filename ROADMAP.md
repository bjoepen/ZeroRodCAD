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
BUILD 022 IN PROGRESS (M1 COMPLETE, M2 NEXT)
```

### Current

Build 022 is in progress. M1 (Tauri Desktop Foundation) is complete; M2 (Productive Sidecar & Rust
Lifecycle) is next.

### Build 022 – Tauri Desktop Foundation

Preparation document: [`docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md`](docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md).

- [x] M1 — productive Tauri v2 application shell (`docs/migration/BUILD-022-M1-TAURI-FOUNDATION.md`)
- [ ] M2 — Rust-owned sidecar process lifecycle (spawn, reuse, timeout, crash/restart, shutdown)
- [ ] M2 — persistent, onedir-packaged Python 3.13 sidecar
- [ ] M2 — existing ZeroRodCAD engine integration (unchanged)
- [ ] M2 — `zerorod-sidecar/v1` adopted stable
- [ ] M2 — `zerorod-mesh/v1` received and validated (not yet rendered)
- [ ] M3 — Three.js preview foundation
- [x] M1 — No-VTK-clean shell (no Python/sidecar dependency yet to violate it)
- [ ] M2 — No-VTK packaging with the TE-002.2B optimized packaging rules as baseline
- [ ] M2 — diagnostics
- [x] M1 — tests (Rust/frontend); M2 adds Python + sidecar-lifecycle tests
- [x] M1 — real app validation pass (launch, IPC bridge, clean shutdown, 0 orphan processes)

Not yet in Build 022: complete parameter UI, complete export UI, full feature parity, PySide6
removal.

### Build 023 – Parameters & Live Preview

- [ ] full `ZeroRodParameters` UI
- [ ] validation
- [ ] live regeneration
- [ ] responsive preview
- [ ] error presentation

### Build 024 – STL / STEP Export Workflow

- [ ] productive STL export
- [ ] productive STEP export
- [ ] native dialogs
- [ ] export status
- [ ] error handling
- [ ] regression comparison with the PySide6 reference app

### Build 025 – Desktop Feature Parity

- [ ] remaining application workflows
- [ ] settings
- [ ] project open/save
- [ ] shortcuts
- [ ] desktop integration
- [ ] accessibility
- [ ] parity validation

### Build 026 – Production Packaging & macOS Integration

- [ ] production bundle
- [ ] final dependency audit
- [ ] performance baseline
- [ ] signing preparation
- [ ] notarization preparation
- [ ] release workflow

Signing/notarization is planned only at the build-planning level here; no new signing/notarization
subproject is started by this roadmap entry.

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
