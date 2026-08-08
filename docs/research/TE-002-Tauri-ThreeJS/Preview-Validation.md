# TE-002 — Preview Validation

Automated and manual checks kept clearly separate throughout, per section 32's explicit
instruction — nothing below claims a check happened that didn't.

## AUTOMATED

| Check | Result | Evidence |
|---|---|---|
| Sidecar produces a real, valid `zerorod-mesh/v1` payload from default parameters | PASS | Standalone shell invocation of the compiled binary; `tests/poc/tauri/test_sidecar_novtk_integration.py` |
| Mesh payload passes both Python-side and JS-side validation | PASS | `test_mesh_contract.py::test_real_default_zerorod_scene_is_valid`; `mesh.test.js` full suite |
| `meshEntryToBufferGeometry`/`lineEntryToBufferGeometry` build correct `THREE.BufferGeometry` from the **real** ZeroRod payload (not synthetic data) | PASS | Node script run against the actual sidecar's response (see `Performance.md`), 20 repeated runs, all succeeded |
| Invalid mesh payloads are rejected before reaching the renderer (never crash it) | PASS | `mesh.test.js`: out-of-range indices, non-multiple-of-3 arrays, empty meshes, NaN/Infinity all throw cleanly before any `THREE.Mesh` is constructed |
| `fitCameraToBounds` produces a sensible camera position/target from real bounds, scales with model size, doesn't throw on degenerate bounds | PASS | `scene.test.js`, 3 tests |
| Rust `request_preview` correctly parses real success/error response shapes, rejects malformed ones | PASS | `cargo test`, 10/10 |
| Frontend `sidecar.js` correctly maps Rust `PreviewError` shapes to `SidecarTimeoutError`/`SidecarProcessError` | PASS | `sidecar.test.js`, mocked `invoke()`, 4 tests |
| Full Tauri app compiles (`cargo check`, `cargo build` via `tauri dev`) | PASS | Clean compile, no errors |
| Tauri app process launches and a window is registered with the OS | PASS | `ps aux` showed the running `target/debug/te002-tauri` process; `osascript`'s System Events process list showed the app as a foreground GUI process |
| No crash / no error output during the observed dev-session window | PASS | `tauri dev` log showed clean Vite startup, clean Rust compile, clean app launch, no runtime error lines |
| Sidecar produces zero VTK/PySide6 evidence at every checked layer | PASS | See `Runtime-Validation.md` |

## MANUAL / NOT VERIFIED

| Check | Status | Why |
|---|---|---|
| Clicking "Load ZeroRod" inside the actual running Tauri window | **NOT VERIFIED** | Attempted via `osascript`/System Events UI scripting; blocked by macOS Accessibility permissions in this sandboxed session (`"osascript hat keine Berechtigung für den Hilfszugriff"`) — the same class of environment limitation TE-001.2 hit with `screencapture`. Not faked, not silently skipped. |
| Visual confirmation that the rendered model looks correct on screen | **NOT VERIFIED** | Same permission constraint; no screenshot could be captured (attempted in TE-001.2's precedent, same failure mode expected here and not re-attempted redundantly) |
| Rotation via `OrbitControls` | **NOT VERIFIED (interactive)** | `OrbitControls` is a stable, official Three.js addon used exactly per its documented API (`enableDamping`, standard event wiring); not independently re-tested since it is third-party, well-established library behavior outside TE-002's own code — no interactive confirmation possible in this session |
| Zoom via `OrbitControls` | **NOT VERIFIED (interactive)**, same reasoning |
| Window resize handling | **NOT VERIFIED (interactive)** — the `resize` handler (`scene.js`) was code-reviewed (recomputes aspect ratio and renderer size from `container.clientWidth/clientHeight`, standard pattern) but not interactively triggered |
| No visible rendering errors / no crashes during real interaction | **NOT VERIFIED** — no interaction reached this session |

## What closes the gap between "automated" and "actually seen on screen"

Every data transformation in the chain the WebView would perform at runtime — parse the real
sidecar JSON, validate it, build `BufferGeometry` with correct position/index/normal attributes,
compute a camera fit from the real bounds — was exercised against the **exact same real payload**
a live click would produce, outside the WebView but through the identical code path
(`main.js` calls exactly `meshContractToGeometries()` and `fitCameraToBounds()`, both covered
above). What remains genuinely unverified is only the GPU rasterization step itself (does
`WebGLRenderer` actually paint correct pixels) and human-interactive confirmation — not the data
pipeline feeding it.
