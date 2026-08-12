# Build 022 — Completion Record

Status: **COMPLETE**

Build 022 Final Gate: **PASS**

Desktop 2.0 Foundation: **ESTABLISHED**

## What did Build 022 change?

Before Build 022, ZeroRodCAD's only desktop application was the PySide6/Qt app (still fully
functional and unchanged). Research (TE-001 through TE-002.2B) had proven, but not yet built
productively, that a Tauri v2 + Rust process layer + persistent Python sidecar + Three.js
architecture could replace it without touching the CAD engine, at a fraction of the historical
bundle size.

Build 022 carried that proven architecture into the actual productive codebase:

- **M1** — a real `desktop/` Tauri v2 project (Rust crate + TypeScript/Vite frontend), a working
  WebView↔Rust IPC bridge, the security boundary in place from the start.
- **M2** — a productive, persistent Python 3.13 sidecar (`src/zerorod_sidecar/`) and a Rust engine
  manager (`desktop/src-tauri/src/engine.rs`) owning its full lifecycle: lazy spawn, reuse,
  timeout, crash detection, restart-once, graceful shutdown with a forced-kill fallback.
- **M3** — a real Three.js renderer consuming the real `zerorod-mesh/v1` payload: body/rod meshes,
  virtual-string lines, `OrbitControls`, bounds-based camera fit, resize, refresh without stale
  geometry.
- **M4** — a reproducible, hash-gated dylib deduplication step
  (`packaging/tauri/dedup_bundle_dylibs.py`) closing the one TE-002.2B optimization not already in
  place productively, and a one-command build pipeline
  (`scripts/build-productive-desktop-app.sh`).
- **M5** — this milestone: proof that M1–M4 form one coherent, internally consistent, reproducible
  system, not four independently-plausible but never-integrated pieces.

## Why did we change it?

VTK alone accounted for 584.10 MiB of the historical 910.51 MiB PySide6/Qt bundle, none of it
required by ZeroRodCAD's actual CAD workflows. The research phase answered whether removing that
dependency — and modernizing the desktop shell itself — was possible; Build 022 answers whether it
could be done productively, reproducibly, and without regressing anything the existing app already
does. See `docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md` for the full decision record.

## What architecture is now productive?

```text
Tauri v2
    │  bundled local frontend (TypeScript + Vite, no external CDN)
    ▼
Three.js 3D Preview
    │  invoke("engine_*") — the WebView's only IPC surface
    ▼
Rust Process / IPC Layer (owns spawn, lifecycle, timeout, crash handling, shutdown)
    │  private stdin/stdout, zerorod-sidecar/v1
    ▼
Persistent Python 3.13 Sidecar (PyInstaller onedir)
    │
    ▼
ZeroRodCAD Engine (unchanged) → CadQuery 2.8.0 → cadquery-ocp-novtk 7.9.3.1.1
```

Contracts: `zerorod-sidecar/v1` (request/response envelope) and `zerorod-mesh/v1` (renderer-
agnostic mesh transport), both adopted stable from the TE-002 research and unmodified throughout
Build 022 — no protocol reinvention occurred at any milestone.

## Architecture conformance (verified against ADR-022-001, M5)

| Requirement | Status |
|---|---|
| Tauri v2 | ✅ `tauri = { version = "2" }` |
| Three.js | ✅ `"three": "^0.185.1"` |
| Rust owns process lifecycle | ✅ `engine.rs` |
| WebView owns process lifecycle | ✅ NO — 0 shell-plugin imports in frontend source |
| Persistent sidecar | ✅ |
| Python 3.13 | ✅ `.venv-novtk-bundle`: Python 3.13.14 |
| CadQuery | ✅ 2.8.0 |
| cadquery-ocp-novtk | ✅ 7.9.3.1.1 (cadquery-ocp confirmed absent) |
| VTK | ✅ absent (0 files, static + runtime) |
| Productive PySide6/Qt | ✅ absent (0 files) |
| Private stdin/stdout IPC | ✅ no HTTP/WebSocket/gRPC anywhere in `desktop/src-tauri` |
| `zerorod-sidecar/v1` | ✅ present in Python + Rust |
| `zerorod-mesh/v1` | ✅ present in Python + Rust + frontend |
| onedir | ✅ |
| onefile | ✅ absent — no `externalBin` in `tauri.conf.json` |
| Dylib dedup | ✅ hash-gated, symlink-safety-verified, idempotent |

18/18 automated conformance checks pass (`scripts/validate-build022.sh`). Zero deviations from
`ADR-022-001` found or accepted.

## What was proven

- **Functionally**: the real engine produces a real ZeroRod mesh (body: 720 vertices/710
  triangles, rod: 146 vertices/140 triangles, strings: 12 points — unchanged from TE-002's own
  measurement throughout every milestone) through the exact bundled sidecar binary, rendered via
  Three.js, with human-confirmed rotate/zoom/refresh.
- **Reliability**: a real `SIGKILL` crash simulation against the exact bundled binary, at every
  milestone from M2 through M5, confirms no zombie/orphan process — onedir's structural advantage
  over onefile (proven in TE-002.1) holds productively too.
- **Reproducibility**: a completely clean rebuild in M5 (all generated artifacts removed, sidecar
  → stage → Tauri release build → dedup, from scratch) produced a **byte-for-byte identical**
  release bundle to M4's own measurement (299,066,193 bytes / 285.21 MiB / 201 files / 77
  symlinks) — the build is deterministic, not artifact-dependent.
- **Security boundary**: WebView capability stayed `core:default` only and CSP stayed restrictive
  across all five milestones; no milestone ever needed to widen either.
- **Packaging discipline**: TE-002.2B's proven No-VTK/no-onefile/dylib-dedup baseline was carried
  into the productive path exactly, plus one new, individually investigated, safety-first
  exception found only in the productive build (`Python.framework/Python`, ~4.8 MiB, documented in
  `BUILD-022-M4-PRODUCTIVE-PACKAGING.md`).

## Final package size

**285.21 MiB** (299,066,193 bytes / 299.07 decimal MB), release build, 201 files, 57 directories,
77 symlinks, 161 Mach-O binaries — measured twice independently (once in M4, once from a fully
clean rebuild in M5) with identical results.

Within **1.76%** of TE-002.2B's own 280.27 MiB PoC reference (itself a release-build measurement),
with the entire delta explained by one documented ~4.8 MiB dedup exception plus legitimate M1–M3
product code (the Three.js frontend, additional Rust modules). Size Classification: **A** — no
unexplained size remains.

## Final runtime performance

| Metric | M5 final (release, clean rebuild) | Reference range across M2–M4 |
|---|---:|---:|
| Cold start | 0.620 s | 0.612–0.644 s |
| Warm median | 0.1231 s | 0.1216–0.123 s |
| Warm p95 | 0.1265 s | 0.1228–0.1256 s |
| RSS after 20 requests | 321,696 KB | 320,688–326,700 KB |

No material regression at any point across the whole build.

## Accepted limitations

- **`Python.framework/Python` dedup exception** (~4.8 MiB): Tauri's resource-copy step drops the
  `Versions/Current` directory symlink entirely (not just dereferences it); the dedup script
  safely reverts this one pair to a real-file copy rather than force an unsafe relink. Documented,
  not hidden, not "fixed" by expanding scope.
- **Interactive click-through automation**: every milestone in this series (M2, M3, M4) hit the
  same wall — macOS Accessibility permission is not granted in this environment, verified directly
  each time, not assumed from a prior finding. Each milestone's automated evidence closed the gap
  as far as it could (exact bundled binary driven through the real protocol, including real crash
  simulations), and the Project Owner completed the remaining interactive checklist by hand each
  time. All recorded as PASS.
- **`mesh.realpayload.test.ts` occasional timing flake**: this one frontend test spawns the real
  bundled sidecar binary and was observed to intermittently exceed its default timeout under
  concurrent system load (observed twice across M3/M4/M5 sessions, always passing on immediate
  retry in isolation or as part of a quieter test run). Not a functional defect — the underlying
  code path is exercised successfully by every other invocation, including the master validation
  gate's own run.
- **No signing/notarization**: explicitly out of scope for Build 022 (planned for Build 026).

## Explicitly NOT part of Build 022

- Parameter editing / live parameter regeneration UI
- STL/STEP export UI
- Full desktop feature parity (settings, project open/save, shortcuts, accessibility)
- PySide6 retirement (the legacy app is untouched and remains the reference/rollback path)
- Production code signing or notarization

These are Build 023–026 scope by design (see `ROADMAP.md`), not gaps in Build 022 itself.

## Human validation record

| Milestone | Result | Tester | Date |
|---|---|---|---|
| M1 | Real app launch, screenshot-verified (no separate checklist was required by M1's own mandate) | — | 2026-08-09 |
| M2 | PASS | Project Owner | 2026-08-09 |
| M3 | PASS | Project Owner | 2026-08-09 |
| M4 | PASS | Project Owner | 2026-08-09 |
| M5 | Not required — M5 introduced no runtime/product behavior change; M2–M4's human evidence, plus M5's own automated re-validation of the exact final bundle, satisfies Build 022's human-evidence requirement | — | — |

## Milestone matrix

| | Implementation | Engineering | Human | Gate |
|---|---|---|---|---|
| M1 | ✅ `desktop/` Tauri shell | ✅ PASS | N/A (real launch validated) | **COMPLETE** |
| M2 | ✅ `src/zerorod_sidecar/`, `engine.rs` | ✅ PASS | ✅ PASS | **COMPLETE** |
| M3 | ✅ `mesh.ts`/`scene.ts`/`preview.ts` | ✅ PASS | ✅ PASS | **COMPLETE** |
| M4 | ✅ `dedup_bundle_dylibs.py` | ✅ PASS | ✅ PASS | **COMPLETE** |
| M5 | ✅ audits + master gate | ✅ PASS | N/A (no behavior change) | **COMPLETE** |

No contradictory status found anywhere in the documentation tree during M5's consistency audit.

## Reproducing the final build

```bash
./scripts/build-productive-desktop-app.sh release
./scripts/validate-build022.sh
```

Expected final line: `BUILD-022 CONSISTENCY GATE: PASS`.

## Repository state

- `experiments/te002-tauri/`: unmodified throughout Build 022 (verified: 0 diff since the
  docs-consolidation base commit `797519b`).
- Legacy PySide6 app (`src/zerorodcad_desktop/`): unmodified throughout Build 022 (same
  verification).
- No generated build artifact tracked in git at any point (`target/`, `node_modules/`,
  `sidecar-dist/`, `resources/`, `build/` all correctly gitignored).

## Build 022 Final Gate

**PASS.**

- M1 PASS, M2 PASS, M3 PASS, M4 PASS, M5 PASS.
- Architecture conforms to `ADR-022-001` (18/18 checks).
- Final release build reproducible (byte-for-byte identical across two independent builds).
- Complete automated test matrix green: 21 Rust, 41 Python sidecar tests (+282/1-skip full repo),
  53 frontend tests, TypeScript clean, `cargo fmt`/`clippy` clean, `ruff` clean.
- Required human validations PASS (M2, M3, M4).
- No-VTK invariant holds (static + runtime + environment).
- No-PySide6/Qt productive invariant holds.
- Lifecycle invariant holds (persistent reuse, crash recovery, clean shutdown, 0 orphans).
- Security boundary holds (`core:default` only, restrictive CSP, private stdin/stdout).
- Final packaging is explainable (Size Classification A).
- Documentation is consistent (no stale status phrases found in the M5 sweep).

**Build 022: COMPLETE. Desktop 2.0 Foundation: ESTABLISHED.**

## Next

**Build 023 — Parameters & Live Preview.** See `docs/migration/BUILD-023-HANDOFF.md`.
