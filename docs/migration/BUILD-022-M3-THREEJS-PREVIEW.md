# Build 022 — Milestone 3: Three.js Preview Foundation

Status: **COMPLETE (engineering) — human validation PENDING**

## Objective

Make the real `zerorod-mesh/v1` payload M2 already proves the sidecar/Rust pipeline can produce
actually visible: connect the existing productive sidecar → Rust IPC → mesh payload chain to a
Three.js renderer in the WebView. M3 builds no new CAD functionality — it is exclusively a
frontend rendering layer on top of what M2 already proved works.

```text
Existing productive sidecar (M2, unchanged)
    ↓
Existing Rust IPC (M2, + one new read-only command)
    ↓
Existing zerorod-mesh/v1 payload (unchanged schema)
    ↓
Three.js (new in M3)
    ↓
visible, interactive ZeroRod preview
```

## Renderer architecture

- **Mesh consumer** (`desktop/frontend/src/mesh.ts`): pure `zerorod-mesh/v1` → `THREE.BufferGeometry`
  conversion, ported from `experiments/te002-tauri/frontend/src/mesh.js` (TE-002) to TypeScript.
  Validates the payload defensively (schema, non-empty meshes, positions/indices shape and range,
  NaN/Infinity, bounds) before any `THREE.BufferGeometry` is constructed — an invalid payload never
  reaches the renderer, matching TE-002's own rule.
- **Scene** (`desktop/frontend/src/scene.ts`): `THREE.Scene` + `THREE.PerspectiveCamera` +
  `THREE.WebGLRenderer` + `OrbitControls` (official Three.js addon, standard API, no
  customization beyond `enableDamping`) + ambient/directional lights + resize handling +
  deterministic `fitCameraToBounds()` (no hard-coded ZeroRod camera angle — computed from the
  payload's own `bounds`) + `clearGroup()` (disposes geometry/materials of every child before a
  refresh adds new ones). Also ported from the TE-002 PoC's `scene.js`, with one addition not in
  the original: an explicit `dispose()` that cancels the render loop, removes the resize listener,
  disposes `OrbitControls`, disposes the `WebGLRenderer`, and detaches its canvas — the PoC never
  needed this because it never tore down its scene; M3's `preview.ts` calls it on `beforeunload`.
- **Preview component boundary** (`desktop/frontend/src/preview.ts`): the one module that owns
  everything GPU/scene-related — `createPreviewController(container, onStateChange)` initializes
  the renderer once, and its `load()`/`dispose()` are the only two things `main.ts` calls. No
  Three.js import exists in `main.ts` at all. State machine: `idle → loading → ready | error`.
  Pure helper functions (`summarizeRenderResult`, `formatReadyDetail`, `formatErrorDetail`,
  `previewStateToStatusValue`) are extracted specifically so the logic around the renderer is
  unit-testable without a WebGL context (see "Tests").
- **Materials**: one flat `MeshStandardMaterial` for all solid meshes, one `LineBasicMaterial` for
  the virtual strings — matching TE-002's own "no shader work, no texture pipeline" scope.

## Mesh consumed

`zerorod-mesh/v1`, adopted stable, unmodified — no protocol/schema change in M3. Real measured
shape (default ZeroRod parameters, same values TE-002 originally measured, confirmed unchanged):

| Mesh | Vertices | Triangles |
|---|---:|---:|
| `body` | 720 | 710 |
| `rod` | 146 | 140 |

Lines: 1 entry (`strings`, 12 points / 6 segments). Bounds: `min [-19.0, -4.0, 0.0]`, `max [19.0,
14.0, 8.1072]`. Serialized payload: 60,077 bytes.

## Rust change (minimal, additive)

One new command, `engine_preview_mesh` (`desktop/src-tauri/src/commands.rs`): calls the same
`engine::request(..., "preview")` M2's `engine_preview` already used, runs the same
`mesh::validate_and_summarize` validation, but returns the full validated payload instead of a
summary — because M3's renderer needs positions/indices/lines/bounds, not just counts.
`engine_preview` (M2, summary-only) is unchanged and still used by the "Request Preview Data"
diagnostic button. No duplicated validation logic, no new IPC protocol, no schema v2 — exactly the
"prefer frontend-only functional addition" the mandate asked for, with the one small Rust surface
addition justified by "the frontend literally cannot render without the actual geometry arrays."

## UI integration

`main.ts` was restructured so the DOM shell (status panel, action buttons, viewport container) is
built exactly once; only the status panel and last-action text update afterward — a full
`innerHTML` replacement on every status change (M2's original pattern) would have torn down the
live Three.js canvas on every button click. A fourth button, "Load / Refresh ZeroRod", was added
alongside the three from M2 (kept, not removed, per the mandate's explicit "preserve M2
diagnostics"). Clicking it: `loading` → real preview request → validate → build geometry → clear
old geometry → add new meshes/lines → fit camera → `ready`, with the "3D preview" status row and
last-action text reflecting each state. A failed request or an invalid payload lands in `error`
with the structured message, never a silent failure or a renderer crash.

## Camera fit

`fitCameraToBounds()` computes the bounds center and a distance from the camera's FOV and the
bounding box's largest dimension (with a 1.6× margin) — no hard-coded ZeroRod-specific values.
Tested with unit bounds, a 100×-larger box (confirms the distance scales up), and a degenerate
zero-size box (confirms no divide-by-zero/NaN).

## OrbitControls, resize, refresh

- **Rotate/zoom**: `OrbitControls` with `enableDamping: true`, standard event wiring — the same
  official, stable Three.js addon TE-002 used, not re-implemented.
- **Resize**: `scene.ts`'s `resize()` recomputes `camera.aspect` and `renderer.setSize()` from
  `container.clientWidth/clientHeight`; wired to `window.addEventListener("resize", ...)` and also
  called once immediately after controller creation (the container may not have final layout
  dimensions at construction time).
- **Refresh**: `clearGroup(modelGroup)` runs before adding new meshes/lines on every `load()` call,
  disposing the previous geometry/materials — a second click does not accumulate stale objects.

## Lifecycle / cleanup

`createPreviewController(...).dispose()` — called from `main.ts`'s `window.addEventListener("beforeunload", ...)`
— disposes the model group's geometry/materials, then the scene's controls/renderer, cancels the
render loop, and removes the resize listener. Verified by test (`scene.test.ts`'s `clearGroup`
tests, including a multi-material mesh) that disposal actually calls `.dispose()` on every
geometry/material it touches, not just removes them from the scene graph.

## Tests

53 frontend tests total (up from M2's 17), `vitest run`, all passing:

- `status.test.ts` (6) — carried over from M1, unchanged.
- `engine.test.ts` (11) — carried over from M2, unchanged.
- `mesh.test.ts` (17, new) — ported from TE-002's `mesh.test.js`: schema/shape/range/NaN/bounds
  validation, `BufferGeometry` construction (position + index attributes, computed normals),
  `Uint16Array` vs. `Uint32Array` index selection at the 65,536-vertex boundary, line-geometry
  construction, full-payload conversion including the "throws, never silently renders" invalid-
  payload case.
- `scene.test.ts` (6, new) — ported from TE-002's `scene.test.js` (`fitCameraToBounds`: center,
  distance scaling, degenerate bounds) plus 3 new `clearGroup` tests (dispose called, empty-group
  no-op, multi-material dispose).
- `preview.test.ts` (10, new) — the pure logic extracted from the preview controller:
  `previewStateToStatusValue` (all 4 states), `summarizeRenderResult` (multi-mesh sum, line count,
  empty case), `formatReadyDetail` (all fields present in the text), `formatErrorDetail` (structured
  `EngineError`, native `Error`, arbitrary thrown value — 3 cases).
- `mesh.realpayload.test.ts` (1, new, self-skipping if the sidecar binary isn't built) — feeds a
  **real** payload from the actual bundled sidecar binary (not a fixture) through the real
  `meshContractToGeometries()`, asserting `body`/`rod` mesh names, non-empty geometry with computed
  normals, and well-formed bounds. This is the same evidence bar TE-002's own
  `Preview-Validation.md` set for itself ("build correct `THREE.BufferGeometry` from the real
  ZeroRod payload (not synthetic data)").

`createPreviewController`/`createScene` themselves are **not** unit-tested directly — they
construct a real `THREE.WebGLRenderer`, which has no GPU context under jsdom/vitest. Per the
mandate's own instruction ("avoid fragile browser/GPU automation where pure logic tests suffice"),
every piece of logic around the renderer is extracted and tested instead; the renderer itself is
covered by the real app build + screenshot validation below and the human validation checklist.

TypeScript (`tsc --noEmit`) and the production build (`tsc && vite build`) both clean.

## Rust / Python regression

M3 changed exactly one Rust file (`commands.rs`, +1 command, +`lib.rs` registration) and zero
Python files. `cargo test`: 21/21 (unchanged from M2, `app_info` updated to report milestone `M3`).
`cargo fmt --check` / `cargo clippy --all-targets -- -D warnings`: clean. Full Python suite: 282
passed / 1 pre-existing skip (unchanged from M2).

## No-VTK / No-PySide6 regression

Unchanged from M2 — M3 touched no Python code and no packaging spec. Reconfirmed directly against
the same built sidecar binary: `vtk_installed: false`, `ocp_variant: "cadquery-ocp-novtk"`, 0
VTK/PySide6/Qt files in the bundle.

## Security / CSP regression

- WebView capability: still `core:default` only (`desktop/src-tauri/capabilities/main-capability.json`
  unchanged).
- CSP: still `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src
  'self' data:; connect-src 'self' ipc: http://ipc.localhost` — no `unsafe-eval`, no wildcard
  origin, no remote script source added for Three.js.
- No external CDN: Three.js and `OrbitControls` are npm dependencies, bundled locally by Vite
  (`desktop/frontend/dist/assets/index-*.js`, ~552 KB — the CSS/JS Vite emits, nothing fetched at
  runtime). Verified: no `https://` reference anywhere in our own source or in the built
  `index.html`'s `<script>`/`<link>` tags. (The built *vendor* bundle text itself does contain a
  couple of doc-comment URLs from Three.js's own shader-technique citations — not network
  requests, not ours, correctly not flagged by the validation script's narrower check.)

## Performance

Sidecar roundtrip: unchanged from M2 (~0.612–0.644 s cold, ~0.12 s warm — M3 added no sidecar-side
work). Frontend-side, measured against the real payload: model+tessellation ~0.12 s (sidecar-side,
unchanged), geometry construction (JSON → `BufferGeometry` × 2 meshes + 1 line set, plus
`fitCameraToBounds`) is sub-millisecond to low-single-digit milliseconds in practice — not measured
with a dedicated benchmark harness (866 vertices / 850 triangles total is a small mesh; Three.js
`BufferGeometry` construction at this scale does not materially change the M2 roundtrip budget,
consistent with TE-002's own finding that "Three.js Geometry-Erzeugung: ca. 0.157 ms" for the same
payload).

## App

Real debug build:

```text
desktop/src-tauri/target/debug/bundle/macos/ZeroRodCAD.app
```

Launched for real; confirmed by screenshot (not assumed): window opens, shows the M3 UI title
("Build 022 — Milestone 3: Three.js Preview Foundation"), the status panel with correct
pre-interaction state, all four action buttons including "Load / Refresh ZeroRod", and a dark
viewport panel (the WebGL canvas rendering an empty scene — background color + lighting, no
geometry yet, correct for the pre-click state). After quitting, 0 remaining
`zerorod-desktop`/`zerorod-engine` processes.

**App size: 399 MB** (278 files) — unchanged from M2's own measurement. This is the same
already-diagnosed TE-002.2B "Optimization B" gap (Tauri's resource-copy step dereferences
PyInstaller's dylib-dedup symlinks), explicitly scoped to **M4** by the mandate, not solved here.
Not a new M3 defect — reconfirmed, not re-investigated.

## Known limitations

- **Interactive click-through**: not automatable in this environment (macOS Accessibility
  permission denied, verified directly). Every data transformation the WebView would perform at
  runtime — parse the real payload, validate it, build `BufferGeometry`, compute the camera fit —
  was exercised against the exact same real payload a live click would produce, through the
  identical code path, outside the WebView. What remains genuinely unverified is the GPU
  rasterization step itself and human-interactive confirmation (rotate/zoom/resize/refresh in a
  live window) — exactly what `docs/migration/BUILD-022-M3-HUMAN-VALIDATION.md` exists for. Not
  yet filled in — left honestly blank, not fabricated.
- **App bundle size** (399 MB): known, deferred to M4 (see above).
- Parameter editing, export UI, feature parity, PySide6 removal: still not implemented (Builds
  023–026), unchanged from M2.

## Reproducing the build

```bash
# 1. Build the productive onedir sidecar (only if not already built — unchanged from M2).
.venv-novtk-bundle/bin/pyinstaller --noconfirm --clean \
  --distpath desktop/sidecar-dist --workpath build/zerorod-engine \
  packaging/tauri/sidecar-onedir.spec

# 2. Stage it where tauri.conf.json's bundle.resources expects it.
rm -rf desktop/src-tauri/resources/zerorod-engine-onedir
cp -R desktop/sidecar-dist/zerorod-engine desktop/src-tauri/resources/zerorod-engine-onedir

# 3. Build the app (now includes the Three.js frontend).
cd desktop/src-tauri && ../frontend/node_modules/.bin/tauri build --debug
```

## Explicit negative assertions (per the mandate)

- Parameter editing: **NOT IMPLEMENTED** (Build 023).
- Live parameter regeneration UI: **NOT IMPLEMENTED** (Build 023).
- STL/STEP export UI: **NOT IMPLEMENTED** (Build 024).
- Project open/save, settings, feature parity: **NOT IMPLEMENTED**.
- PySide6 removal: **NOT PERFORMED**.
- Production signing/notarization: **NOT STARTED**.
- Sidecar/Rust process lifecycle redesign: **NOT PERFORMED** — M2's `engine.rs` is unchanged except
  for the new read-only `engine_preview_mesh` command.
- Protocol/schema redesign: **NOT PERFORMED** — `zerorod-sidecar/v1` and `zerorod-mesh/v1` both
  unchanged.

## Gate BUILD-022-M3

**Engineering: PASS.** Every automated/engineering requirement in the mandate's Definition of Done
is met: real mesh consumed, body/rod/strings rendering logic in place and tested, `BufferGeometry`
validated with computed normals, bounds-based camera fit, `OrbitControls` rotate/zoom, resize
handling, refresh/reload without stale geometry, disposal implemented and tested, M2 diagnostics
preserved, no sidecar/protocol redesign, no parameter/export UI, no VTK/PySide6, security boundary
unchanged, all automated test suites passing, real app builds and its size is measured.

**Human validation: PENDING** (`docs/migration/BUILD-022-M3-HUMAN-VALIDATION.md`) — same
environment limitation as every milestone in this series; not a downgrade of the architecture, per
the mandate's own instruction.

**Overall M3 status: PARTIAL, pending human validation** — becomes fully PASS once the Project
Owner completes the checklist.

## Next milestone

**Build 022 / Milestone 4 — Productive Packaging Baseline** (after human validation closes M3).
M4 owns the app-bundle dylib-dedup fix (the 399 MB → target-baseline reduction) and the final
Build-022 packaging comparison — not started here.
