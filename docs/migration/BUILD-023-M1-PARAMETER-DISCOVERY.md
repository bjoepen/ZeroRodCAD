# Build 023 / Milestone 1 — Parameter Discovery Report

This document is the empirical discovery record required before any parameter contract
implementation (per the Build 023 M1 mandate). It records what was inspected, what parameters
actually exist, how they are classified, and every conflict found between sources. Nothing in the
contract design (`docs/contracts/ZEROROD-PARAMETERS-V1.md`) or implementation may introduce a
parameter, default, unit, or bound that is not traceable to a source below.

## Sources inspected

Documentation (read in full):

- `README.md`, `ROADMAP.md`
- `docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`
- `docs/migration/BUILD-023-HANDOFF.md`
- `docs/migration/BUILD-022-COMPLETION.md`, `BUILD-022-M4-PRODUCTIVE-PACKAGING.md`

No `CLAUDE.md`, `AGENTS.md`, or `AGENTS.override.md` exist in this repository (confirmed via
directory listing) — no additional binding instructions from those files.

Production/domain code (read in full):

- `src/zerorodcad/parameters.py` — `ZeroRodParameters` dataclass. **This is the single canonical
  parameter model** — confirmed as the shared dependency of the CLI (`cli.py`/`export.py`), the
  project file format (`project.py`), the report generator (`report.py`), the legacy PySide6 UI
  (`zerorodcad_desktop/main_window.py`), and the productive sidecar (`zerorod_sidecar/main.py`
  already imports `zerorodcad.parameters`/`zerorodcad.preview` per the Build 023 handoff).
- `src/zerorodcad/validation.py` — `validate_parameters()` / `ValidationResult`, the single
  existing validation service, already reused by the CLI export path and the legacy UI.
- `src/zerorodcad/model.py`, `geometry.py` — CadQuery geometry construction; read to determine
  which dataclass fields actually drive a cut/extrude/cylinder operation (geometry impact) versus
  which are unused there.
- `src/zerorodcad/preview.py`, `preview_data.py` — tessellation / `PreviewScene` construction (used
  by the productive sidecar via `build_preview_scene`).
- `src/zerorodcad/project.py` — `.zerorod` project file format; confirms
  `ZeroRodParameters.to_dict()`/`.from_dict()` is already the field-name/shape contract used for
  on-disk persistence — the parameter request contract reuses this exact shape rather than
  inventing a second one.
- `src/zerorodcad/report.py`, `export.py` — confirms which fields feed the human-readable report
  and STL/STEP export, and that export re-validates via the same `validate_parameters`.
- `src/zerorodcad_desktop/main_window.py` — legacy PySide6 parameter sidebar: which fields are
  exposed as editable widgets, their `QDoubleSpinBox`/`QSpinBox` `setRange(min, max)` values, and
  the widget→dataclass-field mapping in `_parameters()`/`_load_parameters()`.
- `src/zerorod_sidecar/main.py`, `protocol.py`, `mesh_contract.py` — current sidecar command
  dispatch, the `zerorod-sidecar/v1` envelope, the existing hard-reject of non-empty `parameters`
  in `_run_preview_command`, and `zerorod-mesh/v1`.
- `desktop/src-tauri/src/{commands,engine,protocol,mesh}.rs` — Rust IPC boundary: `engine::request`
  (command-only, no parameters forwarded today), `build_request_line` (hardcodes
  `"parameters": {}`), `EngineError`, mesh validation mirror.
- `desktop/frontend/src/{engine,mesh,main}.ts` — frontend IPC client and the current UI (no
  parameter controls; `main.ts` calls every `engine_*` command with no arguments).
- `tests/test_parameters.py`, `tests/test_validation.py`, `tests/test_zerorod_sidecar_main.py`,
  `tests/test_zerorod_sidecar_persistent.py`, `tests/test_zerorod_sidecar_protocol.py`,
  `tests/test_zerorod_sidecar_mesh_contract.py` — existing behavior-as-specification.
- `scripts/validate-build022.sh`, `validate-build022-m4.sh` — gate patterns reused for
  `scripts/validate-build023-m1.sh`.

Read-only, non-authoritative (per mandate, TE-002 PoC is research evidence, not parameter
semantics authority):

- `experiments/te002-tauri/` — inspected; contains no Python domain/parameter model of its own (no
  `ZeroRodParameters`/`default_parameters` references found), so no conflict is possible with the
  productive engine here. Not modified.
- `tools/poc/tauri/sidecar/` — contains an independent PoC sidecar (`main.py`) used only by its own
  research tests; not part of the productive `zerorod_sidecar` package, not modified.

## Canonical parameter model

`zerorodcad.parameters.ZeroRodParameters` (frozen dataclass) is the sole authoritative parameter
model. It is already reused, unmodified, by every productive consumer (CLI, export, project files,
legacy UI, sidecar). Build 023 M1 does not introduce a second model — the request contract is a
thin, versioned JSON envelope around this dataclass's existing `to_dict()`/`from_dict()` shape.

### Dataclass fields (16) — full inventory

All fields are optional at the Python level (every field has a default; `from_dict` only rejects
*unknown* field names, per `parameters.py:139-142`). "Required/optional" below therefore reflects
domain intent, not a Python-level constraint.

| # | Field | Type | Unit | Default | Geometry impact | Legacy UI | Engine validation (single-field) |
|---|---|---|---|---|---|---|---|
| 1 | `project_name` | str | n/a | `"CBG Open G"` | none (metadata only — not read by `model.py`/`geometry.py`) | `QLineEdit`, no range | none |
| 2 | `body_width` | float | mm | `38.0` | yes (`build_base_body` extrude width) | `QDoubleSpinBox(10.0, 200.0)` | must be `> 0` |
| 3 | `body_depth` | float | mm | `9.0` | yes (`build_base_body` profile depth) | `QDoubleSpinBox(5.0, 30.0)` | must be `> 0` |
| 4 | `fretboard_height` | float | mm | `6.90` | yes (`build_base_body` profile apex) | `QDoubleSpinBox(1.0, 30.0)` | must be `> 0`; **warning** (not error) if `!= 6.90` |
| 5 | `rod_diameter` | float | mm | `3.00` | yes (`build_rod` radius) | `QDoubleSpinBox(0.5, 10.0)` | must be `> 0` |
| 6 | `groove_diameter` | float | mm | `2.94` | yes (`build_groove_cutter` radius) | `QDoubleSpinBox(0.3, 10.0)` | must be `> 0` and `< rod_diameter` (cross-parameter) |
| 7 | `rod_center_z_offset` | float | mm | `-0.75` | yes (via `rod_center_z` property, offsets rod & groove position) | not exposed | none found |
| 8 | `groove_front_clearance` | float | mm | `0.01` | yes (via `groove_center_y` property) | not exposed | none found |
| 9 | `string_gauges_inch` | tuple[float,...] | **inch** (not mm — see Unit Note) | `(0.036, 0.026, 0.017)` | yes (count drives channel cutter count via `string_positions_x`; gauge drives string visual radius in preview lines only, not body/rod solids) | `QLineEdit` free text (comma-separated) + `string_count` `QSpinBox(1, 12)` | each gauge must be `> 0`; count must be `>= 1` |
| 10 | `string_spacing` | float | mm | `10.0` | yes (`string_positions_x`, spacing between channel cutters) | `QDoubleSpinBox(1.0, 30.0)` | none single-field; cross-parameter (below) |
| 11 | `string_inlet_y` | float | mm | `0.0` | yes (channel cutter start point, tangent computation) | not exposed | none single-field; feasibility cross-check (below) |
| 12 | `string_inlet_z` | float | mm | `2.80` | yes (channel cutter start point, tangent computation) | `QDoubleSpinBox(0.0, 20.0)` | none single-field; feasibility cross-check (below) |
| 13 | `channel_diameter` | float | mm | `1.15` | yes (`string_channel_cutter` radius) | `QDoubleSpinBox(0.2, 5.0)` | must be `> 0` |
| 14 | `channel_overrun_at_inlet` | float | mm | `0.8` | yes (`string_channel_cutter` start-point extension) | not exposed | none found |
| 15 | `channel_rod_clearance` | float | mm | `0.05` | yes (via `tangent_clearance_radius`, affects channel/rod tangent geometry) | `QDoubleSpinBox(0.0, 2.0)`, labeled "Rod clearance" in the UI but bound to this field (`main_window.py:407`) | none single-field; feasibility cross-check (below) |
| 16 | `minimum_wall` | float | mm | `1.20` | **no** — not referenced anywhere in `model.py`/`geometry.py`; used only by `validate_parameters`' string-spacing-vs-body-width check | not exposed | not itself range-checked; used as a constant in the cross-parameter rule below |

### Derived values (Category B — computed `@property`, not dataclass fields, not part of the request contract)

`string_count`, `string_positions_x`, `rod_radius`, `groove_radius`, `channel_radius`,
`rod_center_y`, `rod_center_z`, `rod_top_z`, `groove_center_y`, `tangent_clearance_radius`,
`tangent_point_yz`, `channel_contact_y`, `channel_contact_z`, `channel_run`, `channel_rise`,
`string_entry_angle_deg`, `string_diameters_mm`, `string_support_heights`,
`string_heights_over_fretboard`. All are pure functions of the 16 fields above. Not transported in
the request contract (input concern only, per the mesh/parameter separation mandate) — a client
that needs them can recompute from a returned value set, or they are surfaced via
`validate_parameters`'s `ValidationResult.values` for a subset already (`string_count`,
`rod_center_y_mm`, `rod_center_z_mm`, `rod_top_z_mm`, `tangent_y_mm`, `tangent_z_mm`,
`entry_angle_deg`).

### Internal engine constants (Category C — not parameterized anywhere, hardcoded in the domain code)

- `preview.py`: tessellation `tolerance=0.16`/`angular_tolerance=0.35` for the body mesh, `0.10` for
  the rod mesh; virtual-string line extension `start_y - 4.0` / `body_depth + 5.0`.
- `model.py`: `build_base_body`'s `shoulder_z = fretboard_height - 1.35` (a fixed offset, not an
  independent parameter); `build_groove_cutter`'s ±1.0 mm cylinder overrun beyond `body_width`.

These are not exposed in the request contract — no evidence they were ever meant to be
user-editable, and turning them into public API surface without a mandate would violate "no
internal constants become public API unnecessarily" (M1 mandate §8).

### Presentation/UI-only state (Category D)

Legacy PySide6: `body_toggle`/`rod_toggle`/`strings_toggle` visibility checkboxes, status banner
colors, camera reset. Tauri/Three.js (Build 022): `OrbitControls` state, camera fit, resize
handling (`desktop/frontend/src/scene.ts`/`preview.ts`). None of these are `ZeroRodParameters`
fields and none affect geometry.

### Export-only settings (Category E)

`export.py`'s output filenames (`{safe_name}-body.stl`, `{safe_name}-assembly.step`,
`{safe_name}-report.md`, derived from `project_name`) and the output directory argument. Not part
of the parameter request contract (Build 024 scope per the roadmap, and per M1 mandate §32 "no
export work").

## Conflicts found

**One conflict, resolved by authoritative engine behavior:**

- **Legacy UI widget ranges vs. engine validation.** The legacy PySide6 UI's `QDoubleSpinBox`
  `setRange(min, max)` values (documented in the table above) are **not enforced anywhere in
  `zerorodcad.validation.validate_parameters`**. They are Qt widget input-assistance limits only —
  a value outside a spinbox's configured range simply cannot be *typed* into that specific widget,
  but nothing stops `ZeroRodParameters(body_width=5.0)` (below the UI's 10.0 minimum) from being
  constructed directly and passing `validate_parameters` (which only requires `> 0`). **Resolution
  (per M1 mandate §7, "bestimme anhand tatsächlichen Engine-Verhaltens"): `validate_parameters` is
  authoritative.** The UI ranges are recorded above as a documented reference for future UI work
  (Build 023 M2+) but are **not** encoded as contract-level `min`/`max` constraints in
  `zerorod-parameters/v1` — doing so would silently narrow the domain the engine actually accepts,
  which is a scope violation of "engine owns parameter semantics" (M1 mandate §9).

No other conflicts were found. The legacy UI's initial widget values match `ZeroRodParameters`'
defaults exactly (verified: `body_width` 38.0 in both). No second/competing default set, project
file format, or validation implementation exists anywhere in the repository.

## Authority decisions

- **Source of truth: `zerorodcad.parameters.ZeroRodParameters` + `zerorodcad.validation.validate_parameters`.**
  The contract, the Python sidecar, and the TypeScript foundation all defer to this — no new
  validation logic is duplicated in Rust or TypeScript (per M1 mandate §9/§21/§22).
- **Canonical defaults: `zerorodcad.parameters.default_parameters()`** (i.e. `ZeroRodParameters()`
  with no overrides). This is already what the parameterless `preview` command has produced since
  Build 022 M2 — explicit-default requests must be semantically equivalent to it (proven in
  Milestone 1's integration test, see the M1 implementation document).
- **Serialization shape: `ZeroRodParameters.to_dict()`/`.from_dict()`**, already the `.zerorod`
  project file's field-name contract. The `zerorod-parameters/v1` request contract's `values`
  object reuses this shape verbatim rather than inventing new field names.
- **`minimum_wall` is real but validation-only.** It is a genuine dataclass field with a default and
  a documented effect (the string-spacing-vs-body-width cross-parameter check), but it has zero
  effect on the constructed CadQuery solids. Recorded as Category A (user-editable, part of the
  canonical model) with an explicit "no direct geometry impact" note rather than silently
  reclassified as internal — the M1 mandate forbids silent harmonization.

## Cross-parameter validation rules (Level 3), as implemented in `validate_parameters`

1. `body_width > 0`, `body_depth > 0`, `fretboard_height > 0` (single "Body dimensions must be
   positive" error covering all three).
2. `rod_diameter > 0`.
3. `groove_diameter > 0`.
4. `groove_diameter < rod_diameter`.
5. `string_count >= 1` (i.e. `len(string_gauges_inch) >= 1`).
6. every value in `string_gauges_inch` is `> 0`.
7. if `string_count > 1`: `string_spacing * (string_count - 1) + 2 * minimum_wall <= body_width`.
8. `channel_diameter > 0`.
9. geometric feasibility: the string inlet point (`string_inlet_y`, `string_inlet_z`) must lie
   strictly outside the rod's protected tangent-clearance circle (radius
   `rod_radius + channel_radius + channel_rod_clearance` centered at `rod_center_y`,
   `rod_center_z`) — violating this raises `ValueError` inside the `tangent_point_yz` property,
   caught by `validate_parameters` and reported as an error, not a crash.

Non-blocking **warnings** (do not invalidate the parameter set): `fretboard_height != 6.90`;
`string_entry_angle_deg > 45°`.

## Unit note

All fields are millimeters **except `string_gauges_inch`, which is inches** (the name says so
explicitly, and `string_diameters_mm = gauge * 25.4` confirms the conversion). This is the one
unit inconsistency in the domain model — not a defect to silently "fix" in M1 (out of mandate; the
engine's actual behavior is authoritative), but the request contract documentation states it
explicitly per-field rather than assuming a single implicit unit system.

## Open questions

NONE. Every field in the canonical model has a traceable default, a known (or explicitly
`UNKNOWN`-marked) bound, and a known geometry-impact classification. The one soft ambiguity (legacy
UI ranges vs. engine validation) is resolved above, not left open.
