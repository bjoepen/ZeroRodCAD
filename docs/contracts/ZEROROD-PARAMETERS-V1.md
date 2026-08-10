# `zerorod-parameters/v1`

## Purpose

The canonical, versioned request contract for sending explicit ZeroRod parameter values across the
Desktop 2.0 process boundary (WebView → Rust → persistent Python sidecar → ZeroRodCAD engine). It
is the **input** contract; the existing `zerorod-mesh/v1` remains the unrelated **output** contract
(§29 of the Build 023 M1 mandate — the two are not merged).

Established in Build 023 Milestone 1. See
`docs/migration/BUILD-023-M1-PARAMETER-DISCOVERY.md` for the empirical parameter inventory this
contract is built from, and `docs/migration/BUILD-023-M1-PARAMETER-CONTRACT.md` for the
implementation record.

## Where it travels

`zerorod-parameters/v1` is not a new top-level protocol. It is carried inside the existing
`zerorod-sidecar/v1` envelope's `parameters` field:

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "req-...",
  "command": "preview",
  "parameters": {
    "schema": "zerorod-parameters/v1",
    "values": { "...": "ZeroRodParameters fields, see below" }
  }
}
```

- **Omitted or `{}` `parameters`** (unchanged since Build 022): the `preview` command uses
  `zerorodcad.parameters.default_parameters()` — the parameterless preview path is preserved
  exactly, no regression.
- **Non-empty `parameters` without `"schema": "zerorod-parameters/v1"`**: rejected with
  `invalid_parameters_schema` (see Error Model).
- **Non-empty `parameters` with the correct schema**: `values` is parsed into a
  `zerorodcad.parameters.ZeroRodParameters` instance and used for that request.

The `status` command is unaffected. A new `parameters_defaults` command (see below) returns the
canonical default value set in the same envelope shape, so no layer needs to hardcode a second copy
of the defaults (Build 023 M1 mandate §14).

## `values` fields

`values` is exactly `ZeroRodParameters.to_dict()`'s shape (`src/zerorodcad/parameters.py`) — the
same shape already used by `.zerorod` project files (`src/zerorodcad/project.py`). No renaming, no
positional arrays: every field is a named JSON object key.

| Field | JSON type | Unit | Default | Constraint |
|---|---|---|---|---|
| `project_name` | string | n/a | `"CBG Open G"` | none (not geometry-affecting) |
| `body_width` | number | mm | `38.0` | `> 0` |
| `body_depth` | number | mm | `9.0` | `> 0` |
| `fretboard_height` | number | mm | `6.90` | `> 0`; warning (non-blocking) if `!= 6.90` |
| `rod_diameter` | number | mm | `3.00` | `> 0` |
| `groove_diameter` | number | mm | `2.94` | `> 0` and `< rod_diameter` |
| `rod_center_z_offset` | number | mm | `-0.75` | none |
| `groove_front_clearance` | number | mm | `0.01` | none |
| `string_gauges_inch` | array of numbers | **inch** | `[0.036, 0.026, 0.017]` | at least 1 entry; each entry `> 0` |
| `string_spacing` | number | mm | `10.0` | see cross-parameter rule below |
| `string_inlet_y` | number | mm | `0.0` | see feasibility rule below |
| `string_inlet_z` | number | mm | `2.80` | see feasibility rule below |
| `channel_diameter` | number | mm | `1.15` | `> 0` |
| `channel_overrun_at_inlet` | number | mm | `0.8` | none |
| `channel_rod_clearance` | number | mm | `0.05` | see feasibility rule below |
| `minimum_wall` | number | mm | `1.20` | none directly; used by the cross-parameter rule below. Has **no effect on the generated solids** — validation-only (see Discovery Report) |

All numeric fields are plain JSON numbers (IEEE-754 double, matching Python `float` — the engine is
float-based throughout; no string-encoded numbers, no Decimal/BigNumber wrapper, per mandate §12).

Cross-parameter rules (evaluated together, not per-field):

- if more than one string: `string_spacing * (string_count - 1) + 2 * minimum_wall <= body_width`
  (`string_count` = `len(string_gauges_inch)`).
- the string inlet point (`string_inlet_y`, `string_inlet_z`) must lie strictly outside the rod's
  tangent-clearance circle (radius `rod_diameter/2 + channel_diameter/2 + channel_rod_clearance`,
  centered on the rod axis) — otherwise no valid channel tangent point exists.

## Versioning

`values.schema` must be exactly `"zerorod-parameters/v1"`. An unrecognized or missing schema on a
non-empty `parameters` object is a structured `invalid_parameters_schema` error, never a silent
fallback and never a raw exception. Future schema evolution (`zerorod-parameters/v2`) would be a
new, additively-handled schema string — Milestone 1 implements v1 only.

## Validation levels

1. **Structural** (`zerorod_sidecar/parameters_contract.py`): `parameters` is a JSON object;
   `values` is a JSON object; unknown top-level keys in `values` are rejected (mirrors
   `ZeroRodParameters.from_dict`'s existing unknown-field rejection).
2. **Field-level type** (`parameters_contract.py`): each known field must deserialize to its
   expected JSON type (numbers for numeric fields, an array of numbers for `string_gauges_inch`, a
   string for `project_name`).
3. **Cross-parameter/domain** (`zerorodcad.validation.validate_parameters` — reused unmodified, the
   single existing validator): the rules listed above.
4. **Geometry generation** (`zerorodcad.preview.build_preview_scene` / CadQuery): a parameter set
   that passes levels 1–3 but still fails during actual solid construction.

Rust and TypeScript never reimplement levels 2–4 — they forward `values` to the sidecar and treat
the response's structured error as authoritative (mandate §21/§22: domain rules stay engine-near).

## Error model

Every rejected request returns the same `zerorod-sidecar/v1` error envelope already in use
(`{"ok": false, "error": {"code": ..., "message": ...}}`), extended with an optional `details`
object carrying whatever structured context is available (`field`, `actual`, `expected`) — never a
raw Python traceback, Rust panic, or HTML.

| Code | Level | Meaning |
|---|---|---|
| `invalid_parameters_schema` | 1 | `parameters` is non-empty but `values.schema` is missing or not `"zerorod-parameters/v1"` |
| `invalid_parameters` | 1 | `parameters`/`values` is not a JSON object, or `values` contains an unknown field name |
| `invalid_parameter_type` | 2 | a known field's JSON value has the wrong type (e.g. `body_width` as a string) — `details` includes `field`, `actual`, `expected` |
| `invalid_parameters_domain` | 3 | `zerorodcad.validation.validate_parameters` reports one or more domain errors — `details.errors` carries the full list of human-readable messages exactly as the validator produced them (the validator does not itself split "range" from "combination" errors, so this contract does not invent a split it cannot evidence — see Discovery Report §"Authority decisions") |
| `geometry_error` | 4 | `values` passed levels 1–3 but the engine failed to construct the geometry |

`invalid_json`, `invalid_schema` (outer envelope), `invalid_request`, `unknown_command`,
`internal_error`, `invalid_mesh` are pre-existing `zerorod-sidecar/v1` codes, unchanged.

The previously hard-coded `unsupported_parameters` rejection (Build 022 M2's placeholder,
documented in `BUILD-023-HANDOFF.md` as a known limitation to remove) is **removed** in Milestone 1
— this is the intended, mandated protocol-surface change, not an accidental break.

## `parameters_defaults` command

```json
{"schema": "zerorod-sidecar/v1", "request_id": "...", "command": "parameters_defaults", "parameters": {}}
```

Returns:

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "...",
  "ok": true,
  "result": {"schema": "zerorod-parameters/v1", "values": { "...": "default_parameters().to_dict()" }}
}
```

This exists so a future frontend (Build 023 M2+) can populate parameter controls from the single
authoritative default set instead of a hardcoded TypeScript copy (mandate §14). No UI consumes it
in Milestone 1.

## Examples

Explicit canonical defaults (semantically equivalent to omitting `parameters` entirely):

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "req-1",
  "command": "preview",
  "parameters": {
    "schema": "zerorod-parameters/v1",
    "values": {
      "project_name": "CBG Open G",
      "body_width": 38.0,
      "body_depth": 9.0,
      "fretboard_height": 6.90,
      "rod_diameter": 3.00,
      "groove_diameter": 2.94,
      "rod_center_z_offset": -0.75,
      "groove_front_clearance": 0.01,
      "string_gauges_inch": [0.036, 0.026, 0.017],
      "string_spacing": 10.0,
      "string_inlet_y": 0.0,
      "string_inlet_z": 2.80,
      "channel_diameter": 1.15,
      "channel_overrun_at_inlet": 0.8,
      "channel_rod_clearance": 0.05,
      "minimum_wall": 1.20
    }
  }
}
```

A valid, meaningfully different request (wider body, wider string spacing — used as Milestone 1's
"alternate parameter set" geometry-difference proof):

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "req-2",
  "command": "preview",
  "parameters": {
    "schema": "zerorod-parameters/v1",
    "values": {
      "body_width": 50.0,
      "string_spacing": 12.0
    }
  }
}
```

(Fields omitted from `values` fall back to `ZeroRodParameters`' own dataclass defaults, exactly as
`ZeroRodParameters.from_dict` already behaves for partial dictionaries.)

An invalid request (groove not smaller than rod — cross-parameter rule violation):

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "req-3",
  "command": "preview",
  "parameters": {
    "schema": "zerorod-parameters/v1",
    "values": {"groove_diameter": 5.0, "rod_diameter": 3.0}
  }
}
```

produces:

```json
{
  "schema": "zerorod-sidecar/v1",
  "request_id": "req-3",
  "ok": false,
  "error": {
    "code": "invalid_parameters_domain",
    "message": "Groove diameter must be smaller than rod diameter.",
    "details": {"errors": ["Groove diameter must be smaller than rod diameter."]}
  }
}
```

## Compatibility

- `zerorod-mesh/v1` (output) is unchanged.
- The parameterless `preview` command (`parameters: {}` or omitted) behaves identically to Build
  022 — same canonical defaults, same mesh.
- No packaging, security capability, or process-lifecycle change was required to carry this
  contract (still forwarded through the existing private stdin/stdout pipe and the existing
  `zerorod-sidecar/v1` envelope's `parameters` field).
