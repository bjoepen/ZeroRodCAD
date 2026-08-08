# TE-002 — Dependency Governance

Every new dependency introduced for TE-002, evaluated against the governance checklist (section 4)
before use. All versions verified live against the npm registry / crates.io at evaluation time —
not assumed or guessed.

## npm (frontend, `experiments/te002-tauri/frontend/package.json`)

| Package | Version | Purpose | Maintenance | License | Alternative considered |
|---|---|---|---|---|---|
| `@tauri-apps/api` | ^2.11.1 | Tauri v2 core JS API (`invoke`) | Official Tauri project, active, current | MIT/Apache-2.0 | None — this is the mandated frontend shell |
| `@tauri-apps/cli` | ^2.11.4 | Tauri v2 build/dev CLI (devDependency) | Official Tauri project, active, current | MIT/Apache-2.0 | None |
| `three` | ^0.185.1 | 3D rendering (`BufferGeometry`, `WebGLRenderer`, `OrbitControls`) | Official, very active (weekly releases), current stable | MIT | None — mandated per section 5 |
| `vite` | ^8.2.1 | Dev server / bundler | Official Tauri-recommended frontend tooling, active | MIT | None — standard Tauri companion, not a new architectural choice |
| `vitest` | ^4.1.10 (dev) | Frontend test runner | Vite-ecosystem standard, active | MIT | Node's built-in test runner considered; vitest chosen since it already ships with the Vite toolchain TE-002 needs anyway (no extra runtime dependency, only a dev-time one) |
| `jsdom` (dev) | ^30.0.1 | DOM shim for vitest | Actively maintained, standard vitest companion | MIT | None needed beyond this — no full browser automation framework pulled in |

**`@tauri-apps/plugin-shell` was evaluated and then removed** — initially added to let the
frontend call `Command.sidecar()` directly, then dropped once the architecture moved all sidecar
process control into Rust (see `Tauri-Architecture.md`). Not a wasted step: this is exactly the
governance process working as intended — a dependency was added, reconsidered against "möglichst
wenige neue Dependencies" and section 28's minimal-capability goal, and removed once a design
without it proved feasible and *better* (smaller WebView-facing IPC/capability surface).

## Rust crates (`experiments/te002-tauri/src-tauri/Cargo.toml`)

| Crate | Version | Purpose | Maintenance | License | Alternative considered |
|---|---|---|---|---|---|
| `tauri` | 2 (resolves 2.11.5) | Application shell | Official, active | MIT/Apache-2.0 | None — mandated |
| `tauri-build` | 2 (resolves 2.6.3) | Build-time codegen | Official, active | MIT/Apache-2.0 | None |
| `tauri-plugin-shell` | 2 (resolves 2.3.5) | Sidecar process spawning (`ShellExt::sidecar`) | Official, active | MIT/Apache-2.0 | A hand-rolled `std::process::Command` wrapper was considered and rejected — the shell plugin already implements exactly the sidecar-binary-resolution (target-triple suffix lookup, PyInstaller-bundle-relative pathing) TE-002 needs, and is the officially documented way to do this in Tauri v2 |
| `serde` | 1 | JSON (de)serialization derive macros | Official Rust ecosystem standard, active | MIT/Apache-2.0 | None — de facto standard |
| `serde_json` | 1 | JSON value type / parsing | Same ecosystem, active | MIT/Apache-2.0 | None |
| `tokio` | 1 (features = ["time"]) | `tokio::time::timeout` for the sidecar roundtrip | Already pulled in transitively by `tauri` itself (its async runtime); used directly here only for the public `timeout()` helper, not a new runtime dependency | MIT | Rejected: hand-rolled timeout via `std::thread`/channels — `tokio::time::timeout` is the standard, already-present tool for exactly this |

No HTTP server, no WebSocket framework, no gRPC, no new RPC library — the sidecar protocol is
plain stdin/stdout JSON exactly as section 11 specifies, using only `serde_json` (already needed
for any JSON handling in Rust) and Python's standard-library `json`/`sys` module.

## Python (sidecar, `tools/poc/tauri/sidecar/`)

**Zero new Python dependencies.** The sidecar imports only:
- Standard library: `json`, `sys`, `time`, `traceback`, `pathlib`.
- Already-existing ZeroRodCAD/TE-001 code: `zerorodcad.parameters`, `zerorodcad.model`,
  `zerorodcad.preview`, `zerorodcad.preview_data`, `tools.poc.novtk.vtk_import_blocker`.
- Already-provisioned TE-001.1/TE-001.2 packages for the no-VTK CadQuery path
  (`cadquery` 2.8.0 + patch, `cadquery-ocp-novtk` 7.9.3.1.1) — reused, not newly evaluated here;
  see `docs/research/TE-001-No-VTK/Dependencies.md` and
  `docs/research/TE-001.1-CadQuery-NoVTK/Patch-Analysis.md` for their own governance records.

## Explicitly not used (per section 4/28 exclusion list)

Tauri v1, Tauri-v1-era tutorials/config, legacy Three.js `JSONLoader`, an old TJS contract as a
production vertex, abandoned WebGL frameworks, Electron, a new CAD engine, a new Python RPC
library (plain stdin/stdout JSON was sufficient), any WebSocket/HTTP/gRPC framework, and any
`dangerousRemoteDomainIpcAccess`-style broad IPC grant.
