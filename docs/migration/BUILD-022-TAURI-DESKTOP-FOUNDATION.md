# Build 022 — Tauri Desktop Foundation (Preparation)

**This document is preparation, not an implementation order.** It exists so Build 022 can start
from a shared, written understanding of scope, boundaries, and contracts — not so that any of the
work below is authorized to begin by virtue of this document existing. Starting Build 022 remains a
separate, explicit decision.

## Objective

Establish a productive Tauri v2 desktop shell for ZeroRodCAD that carries the proven architectural
principles from TE-002 → TE-002.2B into the real project structure — a working foundation, not a
feature-complete replacement for the PySide6 app.

## Context

`docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md` (Status: Accepted, 2026-08-09) approved a
Tauri v2 + Rust process/IPC layer + persistent Python 3.13 onedir sidecar + Three.js architecture,
based on TE-001 through TE-002.2B and a real human validation of the final optimized proof of
concept. Build 022 is the first productive step of the resulting migration
(`docs/migration/README.md`).

## Preconditions

- ADR-022-001 status is Accepted.
- TE-002.2B Gate F-B is PASS and its human validation is recorded as PASS within implemented PoC
  scope (`docs/research/TE-002.2B-Tauri-Bundle-Optimization/HUMAN-VALIDATION.md`).
- The PySide6 reference application still builds and passes its existing test/validation suite
  (Build 022 must not start from a broken baseline).
- `experiments/te002-tauri/` still builds, so its measured contracts and packaging results remain
  reproducible as a regression reference during Build 022.

## Architecture

Carried over from the ADR without modification for Build 022:

```text
Tauri v2 (WebView UI + Three.js preview)
    │
Rust Process / IPC Layer (owns sidecar lifecycle, timeout, crash handling, shutdown)
    │
Persistent Python 3.13 Sidecar (PyInstaller onedir)
    │
ZeroRodCAD Engine + CadQuery + cadquery-ocp-novtk (unchanged)
```

Contracts: `zerorod-sidecar/v1` (private stdin/stdout JSON protocol) and `zerorod-mesh/v1`
(renderer-agnostic mesh transport), both adopted stable from the experiments — see "Sidecar
contract" / "Mesh contract" below.

## Scope

- A productive Tauri v2 application shell, living in the productive project structure (not inside
  `experiments/`).
- Rust-owned sidecar process lifecycle: spawn, reuse, timeout handling, crash detection/restart,
  shutdown on app exit — same responsibilities TE-002.1 proved out, implemented productively.
- A persistent, `onedir`-packaged Python 3.13 sidecar integrating the existing, unmodified
  ZeroRodCAD engine.
- `zerorod-sidecar/v1` and `zerorod-mesh/v1` implemented as the stable transport/mesh contracts.
- A Three.js preview foundation capable of rendering the default ZeroRod model (body, rod, virtual
  strings) with orbit/zoom interaction, matching what TE-002.2B's human validation already
  confirmed works.
- No-VTK packaging, using the TE-002.2B optimized packaging rules (no onefile fallback,
  OpenCASCADE dylib dedup, `numba`/`llvmlite`/`scipy` excluded) as the baseline configuration.
- Diagnostics sufficient to observe sidecar startup, request/response timing, and shutdown — enough
  to keep the TE-002.2B performance baseline (~0.612 s cold start, ~0.121 s warm median) visible
  going forward, not necessarily a full telemetry system.
- Tests: Rust unit tests for the process/IPC layer, Python tests for the sidecar, frontend tests
  for mesh handling — matching the kind of coverage TE-002 through TE-002.2B already established
  (48/48 sidecar, 17/17 Rust, 30/30 frontend, as a rough shape reference, not a literal target
  count).

## Explicit non-scope

- Complete `ZeroRodParameters` UI (parameter editing) — Build 023.
- Complete export UI (STL/STEP) — Build 024.
- Full desktop feature parity (settings, project open/save, shortcuts, accessibility) — Build 025.
- Production packaging, signing, notarization — Build 026 (preparation only there, too).
- PySide6 removal — not before the Post-026 retirement decision.
- Any change to the CAD engine itself, or a new/rewritten geometry implementation in Rust or
  TypeScript.
- Any change to the `zerorod-sidecar/v1` / `zerorod-mesh/v1` schemas beyond what a concretely
  demonstrated Build 022 need requires — no speculative protocol redesign.
- Deleting or restructuring `experiments/te002-tauri/` — it remains the regression reference.

## Files / areas likely affected

Based on `experiments/te002-tauri/`'s existing structure as the closest analog, a productive
equivalent would likely touch (exact paths to be decided at implementation time, not fixed by this
document):

- A new productive Tauri project root (e.g. `desktop/` or similar — naming not decided here).
- `src-tauri/` — Rust crate: commands, sidecar process management, IPC parsing, capabilities/CSP
  configuration, packaging config (`tauri.conf.json`).
- A frontend source tree — WebView UI, Three.js scene setup, mesh conversion
  (`mesh.js`-equivalent), sidecar invocation (`sidecar.js`-equivalent).
- A Python sidecar package/entry point integrating `zerorodcad.*`, `mesh_contract`-equivalent
  serialization, PyInstaller spec for `onedir` packaging.
- New or extended documentation under `docs/` following this repository's existing conventions
  (`docs/ARCHITECTURE-BUILD022*.md`, `docs/MIGRATION-BUILD022*.md`, matching the Build 020/021
  pattern already in the repo).
- `pyproject.toml` / dependency manifests, if the productive sidecar needs its own dependency
  scoping separate from the PySide6 app's.

None of this is created by this preparation document itself.

## Migration boundaries

- The CAD engine (`zerorodcad.*`) is a boundary Build 022 must not cross with redesign work — only
  integrate it, don't change its algorithms or public shapes.
- The WebView/Rust security boundary (see ADR-022-001 "Security boundary") is a hard boundary:
  no shell, process, or broad filesystem permission is ever granted to the WebView.
- The PySide6 application is a boundary Build 022 must not touch, delete, or degrade.
- `experiments/te002-tauri/` is a boundary Build 022 should treat as read-only reference material,
  not something to build directly on top of or relabel as the product.

## Sidecar contract

Adopt `zerorod-sidecar/v1` as specified in `docs/research/TE-002-Tauri-ThreeJS/Sidecar-Contract.md`
and exercised under the persistent runtime in `docs/research/TE-002.1-Sidecar-Runtime/`: one JSON
request per line on stdin, one JSON response per line on stdout, `schema`/`request_id`/`command`/
`parameters` on requests, `{schema, request_id, ok, result|error}` on responses, structured
`{code, message}` errors only — never a raw traceback. Build 022 may add commands beyond `preview`
only as concretely needed (e.g. a shutdown command, already prototyped as `persistent_shutdown` in
the PoC), not speculatively.

## Mesh contract

Adopt `zerorod-mesh/v1` as specified in `docs/research/TE-002-Tauri-ThreeJS/Mesh-Contract.md`: flat
`positions`/`indices` arrays per named mesh, flat line-segment positions for overlays (e.g. virtual
strings), and a `bounds` box computed over every vertex and line endpoint. No colors/materials/
metadata in v1. Both sidecar-side and frontend-side validation (schema id, array-length invariants,
index range, no NaN/Infinity) should be carried over, not dropped for expedience.

## Packaging requirements

- `onedir` PyInstaller packaging for the productive sidecar; no onefile fallback shipped.
- Reproduce TE-002.2B's dylib-dedup fix (or an equivalent) so Tauri's resource-copy step does not
  silently reintroduce duplicate OpenCASCADE dylibs.
- Exclude `numba`, `llvmlite`, `scipy` unless a concrete Build 022 code path is shown to need them
  (re-open the packaging question with evidence if so — don't silently reintroduce them).
- No VTK, no PySide6/Qt anywhere in the Tauri sidecar or frontend dependency tree.
- Measure the resulting bundle size and compare it explicitly against the ~280.27 MiB TE-002.2B
  reference baseline; document any significant delta and why.

## Security requirements

- WebView capability surface stays limited to `core:default`-style app-registered commands; no
  `@tauri-apps/plugin-shell` or direct process/filesystem API in frontend code.
- Rust owns sidecar spawn, reuse, timeout, crash/restart, and shutdown-on-exit.
- IPC stays private stdin/stdout — no HTTP, WebSocket, or gRPC introduced.
- CSP stays restrictive, matching the TE-002/TE-002.1 baseline (`default-src 'self'; script-src
  'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc:
  http://ipc.localhost`) unless a concrete need requires a narrowly-scoped change, documented as
  such.

## Testing strategy

- Rust: unit tests for command handlers, sidecar process management, response parsing/validation —
  matching the kind of coverage TE-002/TE-002.1 already achieved (10+ parsing tests, 17/17 full
  suite as a reference point).
- Python: sidecar protocol tests (valid/invalid requests, all documented error codes, no traceback
  leakage), mesh-contract validation tests — matching TE-002.2B's 48/48 sidecar suite as a shape
  reference.
- Frontend: mesh-conversion tests (`Uint16Array`/`Uint32Array` branch coverage, invalid-payload
  rejection) — matching TE-002's 30/30 frontend suite as a shape reference.
- Full-repo regression: existing ZeroRodCAD test suite must continue passing unmodified (PySide6
  path untouched).
- Packaging validation: a real `tauri build` output, measured (size, file count) and compared
  against the TE-002.2B baseline, same methodology as `docs/research/TE-002.2B-Tauri-Bundle-Optimization/Size-Comparison.md`.
- Performance validation: cold-start and warm-request benchmarks against the same
  `benchmark_sidecar_runtime.py`-style methodology used in TE-002.1/TE-002.2B, compared against the
  ~0.612 s / ~0.121 s reference baseline.

## Human validation strategy

Every prior TE in this series found that real interactive WebView confirmation cannot be automated
in this environment (macOS Accessibility permissions). Build 022 should budget for the same kind of
real human validation pass TE-002.2B's `HUMAN-VALIDATION.md` performed: app launch, model render
(body/rod/strings), rotate, zoom, and — new for Build 022, since it's a productive rebuild rather
than a PoC — a check that this productive build's behavior matches or exceeds what the PoC already
demonstrated. Any known gap (e.g. parameter editing still not implemented) must be recorded
explicitly as NOT IMPLEMENTED / NOT TESTABLE, not silently omitted or marked PASS.

## Definition of Done

- Productive Tauri v2 shell builds and runs, integrated into the existing ZeroRodCAD repository
  structure and engineering workflow (versioned docs, Definition of Done, validation evidence).
- Rust-owned sidecar lifecycle (spawn, reuse, timeout, crash/restart, shutdown) implemented and
  tested.
- Persistent, `onedir`-packaged Python 3.13 sidecar integrates the unmodified ZeroRodCAD engine.
- `zerorod-sidecar/v1` and `zerorod-mesh/v1` implemented, matching the experiment's schemas.
- Three.js preview renders the default ZeroRod model with working rotate/zoom, human-validated.
- Packaging follows the TE-002.2B baseline (no onefile, dylib dedup, no numba/llvmlite/scipy, no
  VTK, no PySide6/Qt); resulting size measured and compared to ~280.27 MiB.
- Performance measured and compared to ~0.612 s cold start / ~0.121 s warm median.
- Security boundary (WebView capability surface, Rust-owned IPC, restrictive CSP) verified intact.
- Automated test suites (Rust/Python/frontend) pass; existing PySide6 test suite still passes
  unmodified.
- PySide6 application untouched; `experiments/te002-tauri/` untouched (still buildable as a
  reference).
- Human validation pass recorded, including explicit documentation of any known scope gaps.
- Documentation follows existing repository conventions and is updated (architecture, migration,
  release notes as applicable for Build 022).

## Rollback strategy

Build 022 is additive: it introduces a new productive Tauri codebase alongside, not instead of, the
existing PySide6 application. If Build 022 needs to be rolled back, reverting its branch/commits
restores the prior repository state with no PySide6 functionality lost, since Build 022 is not
authorized to modify the PySide6 path. The PySide6 app remains the product's shipped fallback for
the duration of the migration.

## Suggested Git workflow

Follow the existing repository convention visible in its branch history (`spike/te0*` for research,
`feature/build0*` for build work). A suggested pattern for Build 022:

- Branch: `feature/build022-tauri-desktop-foundation` (or milestone-scoped sub-branches,
  `feature/build022-m1-...`, if the build is split into milestones, matching the Build 020/021
  pattern already used in this repository).
- Regular, focused commits scoped to one concern each (Rust process layer, sidecar packaging,
  frontend preview, tests, docs) rather than one large commit.
- PR review before merge to `main`, consistent with the existing merged PR history
  (`spike/te0011-...`, `spike/te002-tauri-threejs-preview`, etc.).

## Suggested commit convention

Matching the convention already used across this repository's recent history (`perf(bundle): ...`,
`docs(research): ...`, `test(poc): ...`, `docs: ...`):

- `feat(desktop): ...` — new productive Tauri/Rust/sidecar functionality
- `test(desktop): ...` — new or updated tests for the productive build
- `docs(migration): ...` / `docs(architecture): ...` — documentation updates
- `perf(desktop): ...` — packaging/performance work
- `fix(desktop): ...` — bug fixes within Build 022's scope

## References

- `docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`
- `docs/migration/README.md`
- `docs/research/TE-002-Tauri-ThreeJS/` (Sidecar-Contract.md, Mesh-Contract.md, Tauri-Architecture.md)
- `docs/research/TE-002.1-Sidecar-Runtime/` (Security.md, Process-Lifecycle.md, Performance.md)
- `docs/research/TE-002.2B-Tauri-Bundle-Optimization/` (Size-Comparison.md, Results.md, HUMAN-VALIDATION.md)
- `experiments/te002-tauri/` (regression reference, not the product)
