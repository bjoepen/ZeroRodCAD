# Build 023 / Milestone 1 — Parameter Model & Request Contract Foundation

## Objective

Establish the canonical, versioned `zerorod-parameters/v1` request contract across the full Desktop
2.0 process boundary (WebView → Rust → persistent Python sidecar → ZeroRodCAD engine), so an
explicit, named parameter set can drive real geometry generation end to end — without building any
UI. This is engineering foundation for Build 023's later milestones (parameter controls, live
preview), not those milestones themselves.

## Discovery

Full record: `docs/migration/BUILD-023-M1-PARAMETER-DISCOVERY.md`. Summary: the canonical parameter
model already existed and was already the sole implementation used everywhere in the repository —
`zerorodcad.parameters.ZeroRodParameters` (16 fields) + `zerorodcad.validation.validate_parameters`.
No second model was found, no competing defaults, no competing validator. One documented, resolved
conflict: legacy PySide6 UI widget ranges are UI convenience limits, not engine-enforced bounds —
`validate_parameters` is authoritative, per the discovery report's "Authority decisions".

## Contract design

Full spec: `docs/contracts/ZEROROD-PARAMETERS-V1.md`. `zerorod-parameters/v1` is carried inside the
existing `zerorod-sidecar/v1` envelope's `parameters` field as `{"schema": "zerorod-parameters/v1",
"values": {...}}`, where `values` is exactly `ZeroRodParameters.to_dict()`'s shape — no new field
names, no positional arrays, no protocol reinvention. Backward compatibility is preserved exactly:
an omitted or `{}` `parameters` object still resolves to `default_parameters()`, the Build 022
M2-M4 behavior.

## Source of truth

Unchanged from discovery: `zerorodcad.parameters.ZeroRodParameters` (structure/defaults) +
`zerorodcad.validation.validate_parameters` (domain rules), both reused without modification.
Neither Rust nor TypeScript reimplements range or cross-parameter rules — see "Validation
architecture" below.

## Python integration

- `src/zerorod_sidecar/parameters_contract.py` (new): `parse_parameters_request()` — Level 1
  (structural: `parameters`/`values` shape) and Level 2 (per-field JSON type) validation, then
  constructs a `ZeroRodParameters` via the existing `.from_dict()` (which already rejects unknown
  field names). `parameters_to_contract()` wraps a `ZeroRodParameters` back into the envelope —
  used by the new `parameters_defaults` command.
- `src/zerorod_sidecar/main.py`'s `_run_preview_command`: now calls `parse_parameters_request()`,
  then the existing `validate_parameters()` (Level 3), then `build_preview_scene()` wrapped to
  distinguish a Level 4 geometry-construction failure (`geometry_error`) from other errors. The
  Build 022 M2 placeholder (`SidecarError("unsupported_parameters", ...)`, hard-rejecting any
  non-empty `parameters`) is **removed** — this was the explicitly mandated protocol-surface change
  documented in `docs/migration/BUILD-023-HANDOFF.md`.
- New `parameters_defaults` command returns the canonical default set in the same envelope shape —
  a single authoritative source a future frontend can query instead of hardcoding a second default
  copy (mandate §14).
- `src/zerorod_sidecar/protocol.py`: `SidecarError`/`error_response()` gained an optional
  `details` field (structured `field`/`expected`/`actual`/`errors` context), additive and
  backward-compatible — omitted entirely from the JSON response when not provided.

## Rust integration

- `desktop/src-tauri/src/protocol.rs`: `build_request_line()` now takes a `parameters: &Value`
  argument (forwarded verbatim — Rust does not interpret its shape); `EngineError` gained an
  optional `details: Option<Value>` field, populated from the sidecar's `error.details` when
  present.
- `desktop/src-tauri/src/engine.rs`: `RunningEngine::send()` and the public `request()` entry point
  now take a `parameters: &Value`/`Value` argument and thread it through, including on the
  crash/timeout restart-and-retry path. All **existing** call sites (`ping`, `status`,
  parameterless `preview`, `shutdown`) pass `serde_json::json!({})`, preserving the exact Build 022
  wire shape and behavior.
- `desktop/src-tauri/src/commands.rs`: two **new** commands — `engine_preview_mesh_with_parameters`
  (takes a `parameters: Value` argument, forwards to the sidecar's `preview` command, validates the
  returned mesh exactly like the existing `engine_preview_mesh`) and `engine_parameters_defaults`
  (round-trips the sidecar's `parameters_defaults` command). Existing commands
  (`engine_ping`/`engine_sidecar_status`/`engine_preview`/`engine_preview_mesh`) are **unchanged in
  signature** — new commands were added rather than modifying existing ones, so no existing
  frontend call site needed to change. Both registered in `lib.rs`'s `invoke_handler!`.
- Rust does not duplicate any domain/range/cross-parameter rule — it only serializes, deserializes,
  and forwards.

## TypeScript foundation

- `desktop/frontend/src/parameters.ts` (new): `ZeroRodParametersValues` interface (mirrors the
  Python dataclass field-for-field), `ParametersRequest`, `buildParametersRequest()`,
  `validateParametersShape()` (Level 1/2 structural/type checks only — deliberately does **not**
  reimplement Level 3 domain rules), `fetchDefaultParameters()` and
  `requestPreviewMeshWithParameters()` (thin `invoke()` wrappers for the two new Rust commands).
- `desktop/frontend/src/engine.ts`: `EngineError` gained an optional `details?: unknown` field,
  mirroring Rust's addition.
- **No UI controls.** Nothing in `main.ts` was touched; `parameters.ts`'s functions are not called
  from any button, form, or event handler. This is contract/type foundation only, per the M1
  mandate.

## Validation architecture

Four levels, each owned by exactly one layer:

1. Structural (parameters/values shape) — Python, `parameters_contract.py`.
2. Field-level type — Python, `parameters_contract.py`.
3. Cross-parameter/domain — Python, `zerorodcad.validation.validate_parameters` (reused,
   unmodified).
4. Geometry generation — Python, `zerorodcad.preview.build_preview_scene` / CadQuery, wrapped to
   produce a distinguishable `geometry_error` rather than a generic `internal_error`.

Rust and TypeScript participate only in transport (serialize/deserialize/forward) and, in
TypeScript's case, an optional pre-send Level 1/2 shape check — never levels 3-4.

## Error model

New codes: `invalid_parameters_schema`, `invalid_parameters`, `invalid_parameter_type`,
`invalid_parameters_domain`, `geometry_error` — full definitions and an example error response in
`docs/contracts/ZEROROD-PARAMETERS-V1.md`. All follow the existing `zerorod-sidecar/v1` error
envelope shape, extended with an optional `details` object. No raw traceback, panic, or HTML ever
reaches the response (verified by
`test_parameters_error_response_never_contains_traceback_text`).

## Compatibility

- Parameterless `preview` (`parameters: {}` or omitted): **unchanged**. Verified — see "Integration
  evidence" below.
- `zerorod-mesh/v1` (output contract): unchanged.
- No packaging, capability, or process-lifecycle change (`packaging/tauri/sidecar-onedir.spec`,
  `tauri.conf.json`, `capabilities/main-capability.json` all untouched).

## Integration evidence

Real (non-mocked) request against the freshly rebuilt productive onedir sidecar binary
(`desktop/sidecar-dist/zerorod-engine/zerorod-engine`, PyInstaller onedir, same spec as Build 022,
rebuilt to include the M1 Python changes — see `scripts/validate-build023-m1.sh` for the exact
commands):

| Scenario | Result |
|---|---|
| A: parameterless `preview` | `ok`, `zerorod-mesh/v1` mesh returned |
| B: `preview` with fully explicit canonical-default `values` | `ok`; **bounds and every mesh's `positions`/`indices` arrays are identical to A** — proven semantic equivalence, not merely "both succeeded" |
| C: `preview` with `{"body_width": 60.0, "string_spacing": 12.0}` | `ok`; mesh valid; X bounds extent grew from 38.0 mm to 60.0 mm — a real, attributable, expected geometry change |
| D: `preview` with `{"groove_diameter": 5.0, "rod_diameter": 3.0}` (invalid: groove not smaller than rod) | structured error, `code: "invalid_parameters_domain"`, `details.errors` containing the exact validator message |
| E: parameterless `preview` sent immediately after D, same persistent process | `ok`, valid mesh — the invalid request did not corrupt the stdout protocol or kill the process |
| F: `shutdown` | `ok`, clean exit, 0 orphan processes afterward (`pgrep -fl zerorod-engine` empty) |

Additionally exercised at the unit level (`tests/test_zerorod_sidecar_main.py`,
`tests/test_zerorod_sidecar_parameters_contract.py`, `tests/test_zerorod_sidecar_persistent.py`):
missing/wrong parameters schema, non-object `values`, unknown field name, wrong field type (with
`details.field` asserted), out-of-range single-field value, invalid cross-parameter combination,
and a valid→invalid→valid request sequence both against the in-process persistent loop and (in
`TestRealPersistentSubprocess`) against the real TE-001.1-patched, VTK-free interpreter.

## Performance

Measured against the freshly rebuilt onedir sidecar, direct subprocess stdin/stdout (no Tauri
layer — same methodology class as the Build 022 baseline's sidecar-level measurements):

| Metric | Build 022 baseline | Build 023 M1 |
|---|---|---|
| Cold start (first `ping`) | ~0.620 s | 0.056 s |
| Warm median (canonical-default explicit `preview`) | ~0.1231 s | 0.121 s |
| Warm median (alternate explicit `preview`) | n/a (not requestable in Build 022) | 0.122 s |
| Warm p95 | ~0.1265 s | 0.123-0.125 s |

No unexplained regression: default-vs-alternate explicit-parameter requests differ by ~0.0015 s
(well within noise), i.e. parameter parsing/validation adds negligible overhead over the existing
tessellation/serialization cost. (The cold-start figure is faster here than the Build 022 baseline
number; both measure "spawn to first response," but the exact harness differs — TE-002.1's
benchmark tooling vs. this milestone's direct script — so the absolute cold figures are not claimed
byte-for-byte comparable, only that no regression is visible.) Full script:
`scripts/validate-build023-m1.sh` reproduces this measurement.

## Security

Unchanged. No new Tauri capability, no new filesystem access, no new external process, no change to
the WebView's `core:default`-only permission set or CSP. The parameter contract travels through the
exact same private stdin/stdout pipe Build 022 already established.

## Regressions

None found. Full repository regression suite: 312 passed, 1 skipped (pre-existing, unrelated —
`tests/poc/novtk/test_checkpoints_integration.py`'s Gate A re-evaluation note). Rust: 25 tests,
`cargo fmt --check` clean, `cargo clippy --all-targets -- -D warnings` clean. Frontend: 66 tests
(7 files), TypeScript clean, `vite build` clean.

## Limitations

- The `geometry_error` code path (Level 4) is implemented defensively but was not empirically
  exercised in M1 — no parameter combination was found that passes `validate_parameters` (Level 3)
  but still fails at actual CadQuery solid construction. This is documented rather than worked
  around with an artificial test input, per the mandate against inventing test categories that
  don't demonstrably exist for the real model.
- `validate_parameters` itself does not internally distinguish "single-field out of range" from
  "cross-parameter combination" — both surface under one `invalid_parameters_domain` code with the
  validator's own message list in `details.errors`. Splitting this further would require either
  forking the authoritative validator (rejected — see the discovery report's "Authority decisions")
  or fragile English-message parsing (rejected as guessing). Documented, not silently worked around.
- No UI consumes `parameters.ts`'s functions or the two new Rust commands yet — intentional, M1
  scope.

## Next milestone

**Build 023 / M2 — Parameter Controls Foundation** (per the roadmap's provisional M1-M5 sequence;
no more specific canonical sequence was found in `ROADMAP.md`/`BUILD-023-HANDOFF.md` to supersede
it). Not started by this milestone.
