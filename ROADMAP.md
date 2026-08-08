# ZeroRodCAD Roadmap

## Leitlinie

Die Roadmap wird evidenzbasiert entwickelt.

Technologieentscheidungen werden nicht allein nach Plausibilität oder Bundlegröße getroffen, sondern über reproduzierbare Technology Evaluations, Messungen und klar definierte Gates abgesichert.

---

## Completed

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

---

## Technology Evaluations

### TE-001 – No-VTK Feasibility

- [x] Isolated Python 3.13 environment
- [x] cadquery-ocp-novtk evaluation
- [x] VTK import blocker
- [x] Runtime and OS-level evidence
- [x] IVtk boundary test
- [x] Root cause identified

**Result:** FAIL for unmodified CadQuery 2.8.0 because CadQuery eagerly imports `vtkmodules`.

### TE-001.1 – CadQuery No-VTK Import Decoupling

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

### TE-001.2 – No-VTK Production Bundle Proof

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

### TE-002 – Tauri v2 + Three.js Preview Architecture

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

Open findings:

- PyInstaller onefile sidecar cold start is too slow (~15 s).
- Human interactive rendering confirmation still required.
- Architecture itself is considered technically sound.

---

## Current

### TE-002.1 – Sidecar Runtime Strategy & Human Validation

Goal: determine the production-worthy sidecar runtime/deployment strategy.

Variants:

- [ ] A – onefile / one-shot baseline
- [ ] B – onedir / one-shot
- [ ] C – persistent sidecar
- [ ] D – persistent + onedir, if useful

Engineering topics:

- [ ] Cold-start benchmark
- [ ] Warm-request benchmark
- [ ] Memory behavior
- [ ] Process cleanup
- [ ] Crash recovery
- [ ] App-close cleanup
- [ ] No-VTK regression
- [ ] No-PySide regression
- [ ] Test `.app` build
- [ ] Runtime strategy recommendation

Human validation:

- [ ] ZeroRod visible
- [ ] body visible
- [ ] rod visible
- [ ] strings visible
- [ ] rotate
- [ ] zoom
- [ ] resize
- [ ] reload
- [ ] clean shutdown
- [ ] no remaining sidecar process

Gates:

- [ ] Gate E-A – Engineering PASS
- [ ] Gate E-B – Human Validation PASS
- [ ] Gate E – Overall PASS

---

## Next Architecture Decision

If Gate E = PASS:

### Architecture Decision – ZeroRodCAD Desktop 2.0

Proposed target:

```text
Tauri v2 GUI
    +
Rust process / IPC layer
    +
Python 3.13 Engine Sidecar
    +
CadQuery + cadquery-ocp-novtk
    +
PreviewMesh / JSON contracts
    +
Three.js
```

Required before productive migration:

- [ ] finalize ADR
- [ ] define CadQuery patch deployment strategy
- [ ] prefer upstream CadQuery fix
- [ ] establish reproducible interim patch mechanism if upstream is unavailable
- [ ] define migration milestones
- [ ] retain PySide6 app as rollback/reference until feature parity

---

## Planned Product Migration

Only after Gate E PASS and final ADR approval.

### Migration M1 – Tauri Product Shell

- [ ] establish productive Tauri v2 application shell
- [ ] formalize sidecar lifecycle
- [ ] production-ready packaging
- [ ] version metadata
- [ ] diagnostics

### Migration M2 – Live Parameter → Preview Workflow

- [ ] expose full `ZeroRodParameters`
- [ ] parameter validation
- [ ] persistent preview requests
- [ ] responsive regeneration
- [ ] error states

### Migration M3 – Export Workflow

- [ ] STL export
- [ ] STEP export
- [ ] native file dialogs
- [ ] export result/status
- [ ] regression comparison with PySide6 reference

### Migration M4 – Desktop Feature Parity

- [ ] settings
- [ ] project/open/save workflow
- [ ] remaining application commands
- [ ] keyboard shortcuts
- [ ] native macOS integration
- [ ] accessibility review

### Migration M5 – Production Packaging

- [ ] app bundle
- [ ] optimized sidecar packaging
- [ ] final bundle analysis
- [ ] startup/runtime performance
- [ ] update/release workflow
- [ ] signing
- [ ] notarization

### Migration M6 – PySide6 Retirement Decision

Only when all functionality has been validated:

- [ ] feature parity confirmed
- [ ] real-world testing complete
- [ ] rollback package archived
- [ ] final architecture review
- [ ] decision whether to remove PySide6 desktop path

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

Until the current architecture gates are complete:

- no deletion of the existing PySide6 application
- no premature Build 022 migration
- no binary mesh protocol without evidence
- no new CAD kernel
- no separate repository for the Tauri experiment
- no full UI redesign inside Technology Evaluations

---

## Decision Principle

The current project direction is no longer:

> Make the existing bundle smaller at any cost.

It is now:

> Preserve the proven ZeroRodCAD engine, minimize unnecessary runtime dependencies, and establish a modern desktop architecture whose boundaries are measurable, testable and reversible.
