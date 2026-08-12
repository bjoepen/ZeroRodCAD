# ADR-022-001: ZeroRodCAD Desktop 2.0 — Tauri v2 + Python Sidecar + Three.js Architecture

Status: Accepted

Date: 2026-08-09

Supersedes: `docs/research/TE-002-Tauri-ThreeJS/ADR-DRAFT.md`,
`docs/research/TE-002.1-Sidecar-Runtime/ADR-DRAFT-TE0021.md` (both kept in place as historical
research record, not deleted — see "Superseded architecture" below).

## Context

ZeroRodCAD's existing desktop application is a PySide6/Qt app whose real macOS bundle size
(910.51 MiB) is dominated by VTK, a dependency the actual ZeroRodCAD CAD workflows — geometry,
tessellation, preview, STL export, STEP export — never use. A sequence of Technology Evaluations
(TE-001 through TE-002.2B) was run to answer two separate questions with reproducible evidence
rather than assumption: (1) can VTK be removed without touching the CAD engine, and (2) is there a
viable, modern desktop-shell replacement for PySide6/Qt that keeps the same engine intact. Both
questions now have evidence-backed answers, and the project owner has reviewed and approved the
resulting architecture, including a real, human-performed interactive validation of the final
optimized proof-of-concept build.

## Problem

The current architecture couples three things that don't need to be coupled: a CAD engine
(CadQuery/OCP-based, pure Python), a desktop GUI shell (PySide6/Qt), and a 3D preview technology
(VTK, driven eagerly at CadQuery's own import time, not opt-in). This coupling costs ~530 MiB of
shipped, unused-by-ZeroRodCAD binary weight, and ties any future desktop-shell modernization to
also reworking the preview stack, and vice versa. The project needed a decision, backed by
measurement rather than plausibility, on whether these three concerns can be cleanly separated and
what should replace the GUI/preview pair without redesigning or rewriting the CAD engine itself.

## Evidence

Each research step below is `COMPLETE`. Full detail lives in its own `docs/research/TE-*/` folder;
this ADR summarizes only what the decision below actually rests on.

| Evaluation | Question | Result | Gate |
|---|---|---|---|
| TE-001 | Does unmodified CadQuery 2.8.0 work without VTK? | FAIL — CadQuery eagerly imports `vtkmodules` at package-import time, independent of whether VTK features are used | — |
| TE-001.1 | Can that import coupling be decoupled with a small, mechanical patch? | PASS — 4 files, lazy/guarded imports at 5 real chokepoints, 0 new dependencies, 0 public API changes, full backward compatibility with VTK installed (`Patch-Analysis.md`) | — |
| TE-001.2 | Does the patch survive a real production PyInstaller bundle? | Gate C PASS, HIGH confidence — real macOS `.app`, 910.51 MiB → 380.12 MiB (−530.39 MiB / −58.25%), VTK = 0 at static, runtime-trace, and OS-mapping level, real-world human test PASS | Gate C: PASS |
| TE-002 | Does Tauri v2 + Python sidecar + Three.js drive the same unmodified engine end-to-end? | Gate D PASS, MEDIUM confidence — full chain proven (ZeroRodCAD → CadQuery/OCP → PreviewMesh → `zerorod-mesh/v1` JSON → Rust/Tauri → Three.js `BufferGeometry`); onefile sidecar cold start (~15 s) flagged as an open UX risk, not resolved here | Gate D: PASS |
| TE-002.1 | What sidecar packaging/runtime strategy is production-worthy? | Gate E-A PASS (engineering) — persistent + onedir: ~0.644 s cold start vs. onefile's ~15–17 s, and onedir has no orphan-process risk under forced kill where onefile does (structural, verified with direct kill tests) | Gate E-A: PASS |
| TE-002.2A | What is the ~673 MiB Tauri bundle actually made of? | Gate F-A PASS — 98.15% of the bundle (660.93 MiB) is sidecar payload (duplicate onefile+onedir packaging, duplicate OpenCASCADE dylibs, numba/llvmlite, scipy); Tauri/Rust/frontend itself is 13.04 MiB; 5 optimization candidates identified, none acted on yet | Gate F-A: PASS |
| TE-002.2B | Are the 5 candidates safe to remove, and does the optimized bundle still work? | Gate F-B PASS — all 5 accepted (root-caused, isolated, rebuilt, regression-tested); final bundle 293,892,882 bytes / ~280.27 MiB / 193 files, −393.07 MiB / −58.37% vs. the TE-002.1 baseline; no performance regression (cold start ~0.612 s, warm median ~0.121 s), no memory regression, VTK = 0, PySide6/Qt = 0 | Gate F-B: PASS |
| TE-002.2B Human Validation | Does the final optimized `.app` actually work for a real person, not just automated tooling? | **PASS within implemented PoC scope** — recorded 2026-08-09 by the Project Owner: app starts, ZeroRod model renders (body, rod, virtual strings), rotate/zoom/preview interaction work. Parameter editing is explicitly **NOT IMPLEMENTED / NOT TESTABLE** in the PoC UI — a scope gap, not a failure (`docs/research/TE-002.2B-Tauri-Bundle-Optimization/HUMAN-VALIDATION.md`) | Gate E-B / F-B human leg: PASS |

Every one of the 48/48 sidecar, 241/1-skip full-repo, 17/17 Rust, and 30/30 frontend automated
tests referenced across TE-002 through TE-002.2B passed at each stage; nothing here was accepted
on "not observed" alone (`TE-002.2B/Conclusion.md`).

**Technology Evaluation Phase: COMPLETE.** No TE-002.3 is planned. Further open product questions
(full parameter UI, export UI, feature parity, packaging polish under real product features) belong
in the migration Builds below, not in another foundational TE, unless a genuinely new architectural
uncertainty emerges that these evaluations did not already cover.

## Considered alternatives

- **Keep PySide6/Qt, remove only VTK.** Evaluated and proven viable on its own (TE-001.1/TE-001.2,
  380.12 MiB, no VTK). Rejected as the *sole* end state because it does not modernize the aging
  Qt/PySide6 toolchain and was explicitly scoped as an intermediate proof, not a target — the
  project owner's direction was to also evaluate a modern shell replacement once No-VTK was proven
  possible.
- **Electron + Python sidecar.** Not built or benchmarked in any TE; explicitly excluded by the
  mandate governing this evaluation series (heavier runtime footprint than Tauri's native WebView,
  no evidence gathered, no further consideration given).
- **HTTP/WebSocket/gRPC IPC to the Python engine instead of a private stdin/stdout protocol.** Not
  built; explicitly excluded by every TE-002.x mandate. A private, Rust-owned stdin/stdout pipe pair
  has no listening socket, no network attack surface, and was the only transport actually evaluated
  (`Security.md`, `TE-002.1-Sidecar-Runtime/Security.md`).
- **PyInstaller onefile sidecar (one-shot or persistent).** Built and benchmarked directly against
  onedir in TE-002.1 (4 real variants: onefile/onedir × one-shot/persistent). Rejected: ~15–17 s
  cold start vs. ~0.64 s, plus a structural orphan-process risk on forced kill that onedir doesn't
  have (`Process-Lifecycle.md`). Kept as a documented fallback code path in the PoC, not deleted,
  but not the recommended default.
- **VTK-based 3D preview (unchanged from the historical app) inside a Tauri shell.** Never seriously
  considered — the entire evaluation series exists because VTK is the dominant unnecessary cost;
  reintroducing it inside a new shell would defeat the purpose. Not built.
- **A binary/packed mesh transport instead of flat JSON (`zerorod-mesh/v1`).** Not built; explicitly
  out of scope per the TE-002 mandate. Flagged as an open question for later if payload size becomes
  a measured problem at production scale, not decided here.

## Decision

ZeroRodCAD Desktop will migrate to a Tauri v2 based architecture as its target desktop platform,
replacing PySide6/Qt as the shell and VTK as the preview technology, while leaving the ZeroRodCAD
CAD engine itself unchanged. This decision is now **ACCEPTED**, based on the evidence chain above
and the project owner's real-world human validation of the final optimized proof of concept.

## Target architecture

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
    └── Persistent Python 3.13 Sidecar
          ├── ZeroRodCAD Engine (unchanged)
          ├── CadQuery 2.8.0 (+ No-VTK import-decoupling patch, TE-001.1)
          ├── cadquery-ocp-novtk
          ├── Geometry
          ├── Tessellation / PreviewMesh
          ├── STL
          └── STEP
```

## Sidecar runtime strategy

**Persistent process, PyInstaller `onedir` packaging.** Not onefile, not one-shot. Cold start
~0.612–0.644 s, warm request ~0.121–0.13 s, no orphan-process risk under forced kill (timeout,
crash-recovery restart, app-exit cleanup) — all measured and compared against the alternatives in
`TE-002.1-Sidecar-Runtime/` and re-confirmed unchanged in `TE-002.2B/Results.md`. The one-shot
onefile path may remain present in the PoC as a documented fallback but is not the production
default.

## Preview strategy

Three.js, driven by a versioned, renderer-agnostic mesh contract, `zerorod-mesh/v1`: flat
`positions`/`indices` float/int arrays per mesh, flat line-segment positions for the virtual
strings overlay, and a `bounds` box computed over every vertex and line endpoint so the initial
camera view always shows the complete model (`TE-002-Tauri-ThreeJS/Mesh-Contract.md`). No
colors/materials/metadata are carried in v1; the frontend uses a single flat `MeshStandardMaterial`.
This contract already proved renderer-agnostic across two independent consumers (the existing
`QPainter`-based PySide6 widget, and Three.js), which is evidence for keeping it stable
independent of this ADR's outcome.

## Packaging strategy

TE-002.2B's optimized configuration is the packaging baseline for Build 022 and beyond:

- persistent + `onedir` (no onefile fallback shipped in the productive build)
- deterministic OpenCASCADE dylib dedup: Tauri's resource-copy step was found to silently undo
  PyInstaller's own symlink-based dylib deduplication; fixed with a hash-gated, dyld-verified
  post-bundle script rather than a spec-level exclude filter (`Optimization-B-Dylibs.md`)
- `numba` and `llvmlite` excluded — traced to an unreachable CadQuery visualization feature via
  static import analysis, import-origin analysis, and a direct runtime check, not "not observed"
  alone (`Optimization-C-Numba-Llvmlite.md`)
- `scipy` excluded — independently investigated, same root cause (`Optimization-D-Scipy.md`)
- No VTK, no PySide6/Qt anywhere in the Tauri runtime

Reference optimized size: **293,892,882 bytes / ~280.27 MiB / 193 files**, a **58.37%** reduction
from the 673.34 MiB TE-002.2A baseline. This is a **reference baseline, not a hard future limit** —
real product features will change it, and every significant change must be measured, not assumed.

## Security boundary

- The WebView never receives shell, process, or filesystem permission. Its only interaction with
  the sidecar is `invoke("persistent_preview")` / `invoke("persistent_shutdown")` (and, where kept,
  `invoke("request_preview")`) through Tauri's `core:default` capability — never
  `@tauri-apps/plugin-shell` or any process API directly.
- Rust owns the sidecar process end-to-end: lifecycle (spawn/reuse), IPC, timeout handling, crash
  detection and restart, and shutdown/cleanup on app exit.
- IPC is a private `zerorod-sidecar/v1` JSON protocol over stdin/stdout — no HTTP, no WebSocket, no
  gRPC, no listening socket. A persistent process has a longer-lived pipe pair than the former
  one-shot design, but the pipes remain private to the parent process and are not exposed to the
  WebView or any network surface (`TE-002.1-Sidecar-Runtime/Security.md`).
- CSP stays restrictive: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost`. No broad
  `dangerousRemoteDomainIpcAccess`-style grant anywhere.
- No raw Python traceback is ever placed in a sidecar response; only structured `{code, message}`
  errors cross the boundary (`TE-002-Tauri-ThreeJS/Sidecar-Contract.md`).

Migration Builds must preserve this boundary; none of it is renegotiated by this ADR.

## Consequences

### Positive consequences

- Removes VTK entirely from the shipped desktop app (0 static files, 0 runtime-trace hits, 0
  OS-level mappings, confirmed across TE-001.2 through TE-002.2B).
- ~58% smaller shipped bundle than the historical PySide6/VTK app, using two independently measured
  comparisons (PySide6 No-VTK: −58.25%; Tauri optimized: −58.37% off its own baseline).
- The CAD engine (`zerorodcad.*`, CadQuery, OCP) is untouched throughout every TE — this is a shell
  and transport migration, not an engine rewrite.
- A clean, versioned, testable contract boundary (`zerorod-sidecar/v1`, `zerorod-mesh/v1`) replaces
  a tightly-coupled in-process Qt/VTK preview widget.
- Modern, actively maintained toolchain (Tauri v2, Three.js current stable) instead of an aging
  PySide6/VTK stack.
- No performance or memory regression measured anywhere in the optimization chain — the smaller
  bundle is not a functionality-for-size tradeoff.

### Negative consequences / trade-offs

- Introduces a second GUI technology stack (Rust/Tauri/TypeScript) alongside Python — real ongoing
  maintenance surface and skills implication, not resolved or minimized by this ADR.
- The CadQuery No-VTK decoupling remains a locally-applied patch, not an upstream fix (see
  "CadQuery patch strategy" below) — an ongoing maintenance liability until resolved.
- Disk footprint per sidecar copy under `onedir` (hundreds of files) is inherently larger than a
  single-file artifact, even after deduplication — accepted as secondary to cold-start latency and
  process-termination reliability, not free.
- Full desktop-app feature parity (parameter editing, export UI, settings, project open/save,
  shortcuts, accessibility) is completely unaddressed by TE-001 through TE-002.2B — this ADR
  authorizes only the proven architectural slice, not a finished product.

### Known risks

- Interactive WebView confirmation has, across every TE in this series, only ever been closed by a
  human tester outside the automated sandbox (macOS Accessibility permissions block automation) —
  Build 022 onward must keep budgeting for real human validation passes, not assume automated
  coverage is sufficient.
- No idle-timeout cleanup exists yet for the persistent engine; it stays resident until an explicit
  shutdown, app exit, or crash-triggered restart. A production build should design one.
- Memory growth was only measured over 20 requests (~0.26–0.35% growth); long-session drift is
  unconfirmed.
- The `numba`/`llvmlite`/`scipy` exclusions and the dylib-dedup fix are correct **for the
  CadQuery/ZeroRodCAD code paths exercised so far**; any future dependency on these libraries (e.g.
  a new export format, a new visualization feature) would need to re-open that packaging question,
  not silently reintroduce them unmeasured.
- Parameter editing, export UI, and full feature parity are unbuilt; shipping any Build before
  parity is reached must not be mistaken for the migration being complete.

## Migration strategy

See `docs/migration/README.md` for the full narrative and `docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md`
for the next concrete step. Summary of the build sequence this ADR authorizes planning for (not
implementation, beyond Build 022's own preparation document):

1. **Build 022 – Tauri Desktop Foundation**: productive Tauri v2 shell, Rust process/IPC layer,
   persistent onedir sidecar, existing engine integration, `zerorod-sidecar/v1`/`zerorod-mesh/v1`
   carried over unchanged, No-VTK + TE-002.2B packaging baseline, diagnostics, tests. Not yet:
   parameter UI, export UI, feature parity, PySide6 removal.
2. **Build 023 – Parameters & Live Preview**: full `ZeroRodParameters` UI, validation, live
   regeneration, responsive preview, error presentation.
3. **Build 024 – STL / STEP Export Workflow**: productive export, native dialogs, status/error
   handling, regression comparison against the PySide6 reference.
4. **Build 025 – Desktop Feature Parity**: remaining workflows, settings, project open/save,
   shortcuts, desktop integration, accessibility.
5. **Build 026 – Production Packaging & macOS Integration**: production bundle, final dependency
   audit, performance baseline, signing/notarization *preparation* only.
6. **Post-Build-026 – PySide6 Retirement Decision**: only after feature parity, real-world
   validation, and a rollback archive exist.

Each build keeps the proven contracts (`zerorod-sidecar/v1`, `zerorod-mesh/v1`) and the TE-002.2B
packaging baseline unless a concretely demonstrated product need forces a change, and each
significant packaging or performance change must be measured against the TE-002.2B baseline
(~280.27 MiB, ~0.612 s cold start, ~0.121 s warm median), not assumed safe.

## Rollback strategy

The existing PySide6 desktop application is not modified, degraded, or removed by this decision. It
remains a fully functional reference and rollback path throughout the migration (see "Superseded
architecture" below). Within the Tauri PoC itself, the one-shot onefile sidecar path was
deliberately kept working alongside the persistent onedir path rather than deleted, so reverting the
*runtime strategy* specifically remains possible without new work if a future build ever needed it.
No irreversible step (dependency removal, PySide6 deletion, experiment deletion) is authorized by
this ADR.

## Superseded architecture

The PySide6/Qt + VTK desktop path is **superseded as the target architecture** by this decision, but
is **not removed from the repository**. It remains:

- the functional reference implementation
- the feature-parity reference during migration
- the rollback path until the Tauri migration is fully validated

Removal requires, at minimum: feature parity reached, real-world validation of the Tauri app
completed, migration completion, and an explicit, separate retirement decision (see Build
sequence step 6 above and `ROADMAP.md`). Nothing in this ADR authorizes deleting PySide6 code now.

## CadQuery patch strategy

The No-VTK import-decoupling path depends on the patch proven in TE-001.1 (4 files, lazy/guarded
imports at 5 chokepoints, 0 API changes, full VTK-installed backward compatibility —
`TE-001.1-CadQuery-NoVTK/Patch-Analysis.md`) or a functionally equivalent upstream fix. This
dependency is **not hidden** by the migration:

- **Preferred long-term solution:** an upstream CadQuery fix (the patch was designed to be a
  plausible upstream PR shape, not a permanent fork — see `Patch-Analysis.md`'s "Relation to
  CadQuery/cadquery#1908").
- **Interim solution:** a version-pinned, reproducible local patch (already captured as unified
  diffs against CadQuery 2.8.0 in `docs/research/TE-001.1-CadQuery-NoVTK/patches/`).
- **Explicitly not preferred:** a permanent fork of CadQuery. If upstream acceptance does not
  happen, the fallback is the pinned/reproducible local patch, kept visible and tracked — not an
  unmaintained silent fork.

Every migration Build that touches packaging or dependency versions must keep this patch's
applicability visible (e.g. in dependency audit docs), not assume it stays applied by accident.

## PySide6 status

PySide6 is **not deleted now**. See "Superseded architecture" above — it stays as reference,
feature-parity baseline, and rollback path until an explicit, separate retirement decision is made
after Build 026.

## References

- `docs/research/TE-001-No-VTK/`
- `docs/research/TE-001.1-CadQuery-NoVTK/`
- `docs/research/TE-001.2-NoVTK-Bundle/`
- `docs/research/TE-002-Tauri-ThreeJS/` (including the superseded `ADR-DRAFT.md`)
- `docs/research/TE-002.1-Sidecar-Runtime/` (including the superseded `ADR-DRAFT-TE0021.md`)
- `docs/research/TE-002.2A-Tauri-Bundle-Discovery/`
- `docs/research/TE-002.2B-Tauri-Bundle-Optimization/` (including `HUMAN-VALIDATION.md`)
- `docs/migration/README.md`
- `docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md`
- `ROADMAP.md`
