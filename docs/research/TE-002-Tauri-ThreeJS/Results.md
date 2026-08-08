# TE-002 — Results

## No-VTK / no-PySide6 proof (section 23)

| Evidence layer | Result |
|---|---|
| `vtk` package installed in sidecar's build env (`.venv-novtk-bundle`) | No (`pip show vtk` → not found) |
| `cadquery-ocp` installed | No (`pip show cadquery-ocp` → not found) |
| `cadquery-ocp-novtk` installed | Yes, 7.9.3.1.1 |
| `PySide6` installed/imported anywhere in the sidecar | No — never imported, never a dependency |
| `sys.modules` after a real `preview` request (subprocess-probed) | `vtk_hits: []`, `pyside_hits: []` |
| Static string search of the compiled sidecar binary | `vtkmodules`: 0 occurrences, `PySide6`: 0 occurrences |
| Build 021 M1 runtime trace (reused, not duplicated), real preview request against the compiled binary | `vtk_evidence()` → `[]`; 1150 python_modules / 42 native_extensions observed, none VTK-rooted |
| OS-level (`lsof`/`vmmap`) against the live sidecar process | 0 real "vtk" tokens (real-token regex, excludes the harmless "novtk" substring false positive) — captured while the process was blocked on stdin before import, see caveat below |

**Caveat on the OS-level check**: the live-process snapshot was taken while the sidecar was
blocked waiting for its one stdin line (before `cadquery`/OCP get imported), because the actual
model-build-plus-response cycle completes in ~0.15 s once started — too fast to reliably attach
`lsof`/`vmmap` mid-flight without adding artificial delay to the sidecar (which would be scope
creep). This snapshot is real and honestly obtained, but is a pre-import state, not a mid-request
one. The runtime trace (which *does* cover the full request lifecycle, including the actual
`cadquery`/OCP import and tessellation) and the binary-level `strings` search (which proves VTK
code isn't even present in the executable to be loaded) together close this gap — between them,
every stage of the process's life is covered by at least one clean evidence layer.

## Functional results

| Checkpoint | Result |
|---|---|
| Real ZeroRod model built (default parameters) | PASS — 720+146 vertices, 710+140 triangles, matches TE-001/TE-001.1/TE-001.2 exactly |
| `PreviewMesh` → `zerorod-mesh/v1` serialization | PASS — schema-valid, passes both Python and JS validation |
| Sidecar round trip (real binary, standalone shell/subprocess) | PASS — 100% success rate across all runs in this session |
| Rust `request_preview` response parsing (real and synthetic responses) | PASS — 10/10 `cargo test` |
| Frontend geometry construction from the real payload | PASS — 20/20 successful runs, correct vertex/index/normal attribute counts |
| Error paths (unknown command, invalid JSON, wrong schema, nonzero exit, malformed output, request_id mismatch, missing result) | PASS at every layer (sidecar, Rust, frontend) — all produce clean, structured errors, never a crash or raw traceback |
| Tauri app compiles and launches | PASS |
| Live interactive confirmation (click, rotate, zoom, visual correctness) | **NOT VERIFIED** — environment permission constraint, see `Preview-Validation.md` |

## Test suite summary

- Python (`pytest tests/poc/tauri/`): all sidecar/protocol/mesh-contract tests pass (exact count in
  validation script output — see `scripts/validate-te002-tauri-threejs.sh`).
- Rust (`cargo test`, `experiments/te002-tauri/src-tauri/`): 10/10 passing.
- Frontend (`npm run test`, vitest): 25/25 passing.
- No regressions in the existing ZeroRodCAD test suite (`pytest -q` at repo root) — TE-002 added
  new files only, touched nothing under `src/zerorodcad*`.

## Architecture questions (section 34) — answered here, elaborated in Conclusion.md

See `Conclusion.md` for the full numbered answers. Summary: Tauri v2 + a Python sidecar + plain
stdin/stdout JSON + `PreviewMesh` + Three.js `BufferGeometry` all worked, cleanly and without any
VTK/PySide6 requirement, at every layer this session could reach. The one substantive risk
surfaced is packaging-level (onefile sidecar startup latency, see `Performance.md`), not
architectural.
