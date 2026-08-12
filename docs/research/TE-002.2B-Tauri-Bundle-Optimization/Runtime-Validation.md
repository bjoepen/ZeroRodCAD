# TE-002.2B — Runtime Validation (Final Combined Candidate)

All checks below run against the actual built artifact:
`experiments/te002-tauri/src-tauri/target/release/bundle/macos/ZeroRodCAD TE-002.1.app`
(A+B+C+D applied), specifically its bundled
`Contents/Resources/zerorod-engine-onedir/zerorod-engine` binary — the exact file the shipped app
runs, not a separate copy.

## Functional validation matrix

| Check | Result |
|---|---|
| Tauri app launch (`open`, real `.app`) | PASS — main process running, confirmed via `ps aux` |
| App kill / exit cleanup | PASS — 0 processes remaining after kill (no sidecar had started; matches TE-002.1's own "lazy start" design — nothing to orphan until first request) |
| Persistent sidecar startup (bundled binary) | PASS — cold start 0.612 s |
| Preview, default params | PASS — real protocol round trip, mesh = 720 body + 146 rod vertices, matches the TE-001–TE-002.1 reference exactly |
| Preview, alternate params (library level — protocol itself rejects non-default params, see `Runtime-Evidence.md`) | PASS — via `export-probe`/`preview-alt-probe` stimulus traces |
| Three.js payload valid | Not independently re-verified here (unchanged mesh-contract schema, unchanged frontend code — TE-002.1's own validation applies; interactive WebView click remains outside this environment's automation reach, same limitation TE-002.1 documented) |
| STL export | PASS — `cbg-open-g-body.stl` created |
| STEP export | PASS — `cbg-open-g-assembly.step` created |
| Repeated preview requests (persistent, same process) | PASS — 4 additional requests after the first, all `ok: true` |
| Invalid-parameter error path | PASS — `unsupported_parameters` correctly returned, protocol loop stayed alive |
| Shutdown | PASS — `shutdown` response `ok: true`, process exit code 0 |
| Timeout / crash recovery | Not independently re-tested for this candidate — unchanged from TE-002.1 (`persistent.rs` logic untouched; Optimization A/B/C/D are packaging/dependency-only changes, no Rust process-management code was modified) |
| No orphan processes | PASS — `ps aux` empty for `zerorod-engine` after every test run |

## No-VTK / No-PySide6 (final candidate)

| Method | Result |
|---|---|
| Static `find` scan of built `.app` for `vtk`/`IVtk`/`PySide`/`Qt` | 0 matches |
| Runtime trace (`export-probe`, final bundled binary) | 0 real `vtkmodules.*` hits — only the 2 known false positives (`cadquery.occ_impl.exporters.vtk`, `tools.poc.novtk.vtk_import_blocker`), same as every prior TE in this series; 0 PySide/Qt hits |

## Automated test suites (unchanged code paths, run against the final state)

| Suite | Result |
|---|---|
| `pytest tests/poc/tauri/ -q` | 48/48 pass |
| `pytest -q` (full repo) | 241 passed, 1 pre-existing unrelated skip (identical to pre-TE-002.2B baseline) |
| `cargo test` (`experiments/te002-tauri/src-tauri`) | 17/17 pass (15 unit + 2 onedir integration) |
| `npm run test -- --run` (frontend) | 30/30 pass |

## Security surface (unchanged)

- `experiments/te002-tauri/src-tauri/capabilities/main-capability.json`: still `core:default` only
  — no shell/process/filesystem permission granted to the WebView. Not modified by any
  optimization.
- `tauri.conf.json`'s `app.security.csp`: not modified.
- Process control: still entirely in Rust (`persistent.rs`/`sidecar.rs`), untouched by any of the
  four optimizations — all four are packaging/dependency-exclusion changes, zero Rust logic
  changed.
