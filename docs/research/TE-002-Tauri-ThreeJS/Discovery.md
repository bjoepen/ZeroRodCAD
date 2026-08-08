# TE-002 — Discovery

Technology Evaluation, branch `spike/te002-tauri-threejs-preview` (from
`spike/te0012-novtk-production-bundle`). Not a production migration — the existing PySide6 app
(`src/zerorodcad_desktop/`) is completely untouched by this evaluation.

## Research question

Can a Tauri v2 desktop frontend, via a Python sidecar contract, produce a real ZeroRod model and
render its mesh with Three.js as an interactive 3D preview — without VTK and without PySide6 in
this new GUI path?

## Prior TE documentation used (not re-investigated)

- **TE-001** (`docs/research/TE-001-No-VTK/`): confirmed ZeroRodCAD's own engine never needs VTK;
  established the `VTKImportBlocker` and the no-VTK package strategy (`cadquery-ocp-novtk`
  7.9.3.1.1). Reused verbatim (`tools/poc/novtk/vtk_import_blocker.py`).
- **TE-001.1** (`docs/research/TE-001.1-CadQuery-NoVTK/`): the exact, already-validated CadQuery
  2.8.0 patch (4 files: `shapes.py`, `exporters/vtk.py`, `assembly.py`, `exporters/assembly.py`).
  Reused verbatim — copied from `.venv-novtk-poc`'s already-patched install, not redesigned.
- **TE-001.2** (`docs/research/TE-001.2-NoVTK-Bundle/`): proved the patched, no-VTK path survives
  real PyInstaller packaging (58.25% bundle-size reduction, 0 VTK). Its `.venv-novtk-bundle`
  environment (cadquery-ocp-novtk + patch + PyInstaller, already provisioned) was reused directly
  to build TE-002's sidecar executable — no new environment created from scratch.
- Known false positive (both TE-001.1 and TE-001.2): a module legitimately named
  `cadquery.occ_impl.exporters.vtk` must not be flagged as VTK evidence merely because "vtk"
  appears in its name/path. The corrected, path-segment/dotted-root-based heuristic
  (`tools/poc/novtk/runtime_trace_adapter.py:vtk_evidence()`) was reused as-is for TE-002's own
  runtime-trace check.

## ZeroRodCAD preview architecture (already GUI-neutral, minimal adapter needed)

- `zerorodcad.parameters.default_parameters() -> ZeroRodParameters` — pure dataclass, real
  physical parameters (body/rod/string geometry), no CAD library dependency.
- `zerorodcad.model.build_body()` / `build_rod()` — real `cadquery.Workplane` geometry.
- `zerorodcad.preview.build_preview_scene(params) -> PreviewScene` — tessellates body and rod via
  `Shape.tessellate()`, plus `build_virtual_strings()` for string line segments.
- `zerorodcad.preview_data`:
  ```python
  Point3D = tuple[float, float, float]
  Triangle = tuple[int, int, int]
  Line3D = tuple[Point3D, Point3D]

  PreviewMesh(name: str, vertices: tuple[Point3D, ...], triangles: tuple[Triangle, ...])
  PreviewScene(meshes: tuple[PreviewMesh, ...], lines: dict[str, tuple[Line3D, ...]])
  ```
  Already framework-agnostic — no CadQuery/OCP/Qt types anywhere in this data model. The *only*
  adapter work needed for TE-002 was flattening `PreviewMesh.vertices`/`.triangles` (tuples of
  3-tuples) into the flat float/int arrays the mesh-transport contract wants, plus computing
  overall bounds — implemented in `tools/poc/tauri/sidecar/mesh_contract.py`, ~70 lines, no
  changes to `preview.py`/`preview_data.py`/`model.py` themselves.
- Real default-parameter output (measured, matches every prior TE exactly): body mesh 720
  vertices/710 triangles, rod mesh 146 vertices/140 triangles, 12 string line points, bounds
  `min=[-19.0,-4.0,0.0] max=[19.0,14.0,8.1072]`.

No existing preview API was replaced or altered.

## Tauri v2 discovery (current official docs, verified live)

- **Sidecar / externalBin**: `tauri.conf.json` → `bundle.externalBin: ["binaries/<name>"]`;
  the actual file must be named `<name>-<target-triple>` (macOS ARM64:
  `<name>-aarch64-apple-darwin`, confirmed via `rustc --print host-tuple`).
  Source: [Embedding External Binaries](https://v2.tauri.app/develop/sidecar/).
- **Process control**: two viable patterns exist —
  1. Frontend calls `Command.sidecar(name).spawn()`/`.execute()` directly via
     `@tauri-apps/plugin-shell`, gated by `shell:allow-spawn`/`shell:allow-execute` capabilities.
  2. A custom `#[tauri::command]` in Rust calls `app.shell().sidecar(name)` internally; the
     WebView only ever invokes that one app command over IPC.
  **TE-002 uses (2)** — smaller WebView-facing capability surface (no shell permission exposed to
  the WebView at all), and matches section 17's "process control belongs in the Rust layer" more
  literally. See `Tauri-Architecture.md` for the full rationale.
- **`Child.write()` cannot close a sidecar's stdin** (confirmed via
  [tauri-apps/plugins-workspace#2136](https://github.com/tauri-apps/plugins-workspace/issues/2136)
  and [tauri-apps/tauri#4440](https://github.com/tauri-apps/tauri/discussions/4440)) — this
  directly shaped the sidecar protocol: it must never block on stdin EOF, only on one
  newline-terminated line (`sys.stdin.readline()`), matching section 11's request/response shape
  exactly.
- **Capabilities**: JSON files under `src-tauri/capabilities/`, referenced by identifier from
  `app.security.capabilities` in `tauri.conf.json`. App-registered commands (via
  `invoke_handler`/`generate_handler!`) are callable by any window with `core:default` — no
  separate per-command permission entry needed, unlike plugin-provided commands.
- **CSP**: `app.security.csp` in `tauri.conf.json`, restrictive value used
  (`default-src 'self'; script-src 'self'; ...`), no `dangerousRemoteDomainIpcAccess`-style
  broad grant anywhere in this PoC.
- Versions verified live against the npm/crates.io registries (not assumed): `@tauri-apps/cli`
  2.11.4, `@tauri-apps/api` 2.11.1, `tauri` (Rust crate) 2.11.5, `tauri-build` 2.6.3,
  `tauri-plugin-shell` 2.3.5 (Rust and npm versions match).

## Three.js discovery (current stable, verified live)

- `three` 0.185.1 (npm registry, verified live).
- Current recommended addon import path is `three/addons/*` (confirmed via the package's own
  `exports` map — `./addons/*` is present alongside the older `./examples/jsm/*`, which still
  exists for compatibility but is not the primary path going forward). Used:
  `three/addons/controls/OrbitControls.js`.
- No `JSONLoader`, no legacy TJS contract anywhere in TE-002 — `BufferGeometry` +
  `BufferAttribute` + `setIndex()` + `computeVertexNormals()` throughout, exactly per section 8's
  minimum requirement list.

## PoC scope note

Per section 9, TE-002 lives entirely under `experiments/te002-tauri/` (Tauri app: `frontend/` +
`src-tauri/`) and `tools/poc/tauri/sidecar/` (the Python sidecar source, mirroring the existing
`tools/poc/novtk/` convention from TE-001). No production file under `src/zerorodcad*`,
`packaging/`, or `src/zerorodcad_desktop/` was modified.
