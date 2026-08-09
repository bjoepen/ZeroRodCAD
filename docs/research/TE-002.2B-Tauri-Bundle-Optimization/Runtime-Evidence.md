# TE-002.2B — Runtime Evidence (Phase 0)

## Four real traces captured (not simulated), via `tools/poc/tauri/capture_runtime_trace.py`

Each trace runs the actual onedir sidecar binary (`--persistent`) with the runtime-trace hook
enabled, driving one real protocol round trip where applicable. Raw + parsed JSON under
`build/reports/te0022b-bundle-optimization/runtime-trace/` (not committed, gitignored under
`build/`, same as TE-002.1's own trace artifacts).

| Workflow | Profile | How exercised | scipy | numba | llvmlite | python_modules | native_extensions |
|---|---|---|---:|---:|---:|---:|---:|
| Preview, default params | `preview-probe` | real `preview` protocol request + exit-time stimulus | 0 | 0 | 0 | 1150 | 42 |
| Preview, alternate params | `preview-alt-probe` (new) | exit-time stimulus only — see note below | 0 | 0 | 0 | 1149 | 42 |
| STL + STEP export | `export-probe` | exit-time stimulus, `export_project()` (writes both files) | 0 | 0 | 0 | 1149 | 42 |
| Invalid-parameter error path | `error-probe` (new) | exit-time stimulus, `export_project()` with `body_width=0` | 0 | 0 | 0 | 330 | 25 |

Classification for all three candidates, across all four workflows: **NOT OBSERVED**, upgraded
from TE-002.2A's single-trace finding to a 4-workflow finding. See `Import-Origins.md` for why
this is stronger than "not yet observed" — the actual import path is understood and confirmed
unreachable from ZeroRodCAD's code.

## Why "preview with alternate parameters" and "STL/STEP export" needed a workaround

`tools/poc/tauri/sidecar/main.py`'s `preview` command hard-rejects any non-empty `parameters`
(`SidecarError("unsupported_parameters", "the 'preview' command only supports default ZeroRod
parameters in TE-002")`), and `COMMANDS` has no STL/STEP export command — this PoC's protocol
surface is narrower than the full `zerorodcad` library. Both workflows are real and tested at the
library level (the level PyInstaller's static analysis actually cares about for dependency
collection), via two new stimulus profiles added to the existing trace-hook mechanism
(`packaging/macos/runtime_hook.py`, profile constants in `src/zerorod_analysis/runtime/schema.py`):

- `PROFILE_PREVIEW_ALT_PROBE` — `build_preview_scene()` with `ZeroRodParameters(string_gauges_inch=(0.040, 0.030, 0.020, 0.012), string_spacing=8.0)`, the exact same 4-string alternate set already proven valid by `tests/test_preview.py::test_virtual_strings_follow_string_count` — not a new geometry assumption.
- `PROFILE_ERROR_PROBE` — `export_project()` with `ZeroRodParameters(body_width=0)`, the exact same invalid set already proven to raise `ValueError` by `tests/test_export.py::test_export_rejects_invalid_parameters`.

Both are additive profile-dispatch branches on the *existing* stimulus mechanism (same recorder,
same `sys.addaudithook`, same `trace_runtime.py`-style evidence parsing) — not a new trace engine,
per the mandate's explicit constraint.

## The error path's low module count is itself informative

`error-probe` shows only 330 python_modules / 25 native_extensions vs. ~1150 / 42 for the other
three — because `export_project()` calls `validate_parameters()` *before* its "deliberately lazy"
`from cadquery import exporters` import (`src/zerorodcad/export.py`). An invalid parameter set is
rejected before CadQuery, OCP, or any of its dependencies are ever imported. This is a genuine,
useful finding about the validation architecture, not a gap in the trace.

## Ground-truth cross-check (beyond the 4 traces)

`import cadquery` alone (before any ZeroRodCAD code runs, in the exact `.venv-novtk-bundle`
environment used to build the sidecar) loads zero `numba`/`scipy`/`llvmlite` modules into
`sys.modules` — confirmed directly, not inferred from the trace. See `Import-Origins.md`.
