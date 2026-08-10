# Build 023 — Parameters & Live Preview — Completion Record

## Objective

Build 023 extended the Build 022 Desktop 2.0 foundation (Tauri v2 + Rust process layer + persistent
Python sidecar + Three.js preview, established with no parameter UI and no live regeneration) into a
full parameter-editing and live-preview capability: a productive parameter panel driving the real
ZeroRodCAD/CadQuery engine, with automatic, debounced regeneration that a user experiences as "the
model follows my edits," not "I have to remember to click a button."

## Scope

Five milestones, each building strictly on the previous one, no parallel/competing implementation
introduced at any point:

- **M1 — Parameter Model & Request Contract Foundation**: established `zerorod-parameters/v1`, the
  canonical request contract for sending explicit parameter values across the process boundary.
- **M2 — Parameter Controls Foundation**: built the visible, editable parameter panel — all 16
  fields, canonical defaults, local draft/dirty state, local validation. No engine connection yet.
- **M3 — Parameter-to-Engine Integration**: connected the panel's Apply action to the real engine
  through the M1 contract — the first milestone in which editing parameters from the new UI changed
  real geometry.
- **M4 — Live Preview Behavior & UX**: replaced "you must click Apply" with automatic, debounced
  regeneration, with stale-response protection so rapid edits can never show an outdated result.
- **M5 (this record)** — Integration & Build Completion: proves M1-M4 together form one coherent,
  reproducible, regression-free capability, and closes Build 023.

## M1 outcome

`zerorod-parameters/v1`: a versioned request contract carried inside the existing
`zerorod-sidecar/v1` envelope's `parameters` field, mirroring `zerorodcad.parameters.ZeroRodParameters.to_dict()`'s
shape exactly (no renaming, no positional arrays). 16 fields: 15 geometry-affecting, 1 metadata
(`project_name`). Source of truth: `zerorodcad.parameters.ZeroRodParameters` (structure/defaults) +
`zerorodcad.validation.validate_parameters` (domain rules) — both reused unmodified, never
duplicated in Rust or TypeScript. A new `parameters_defaults` sidecar command lets every later layer
fetch canonical defaults from one place instead of hardcoding a second copy. Proven end to end
against the real bundled sidecar: canonical-default equivalence, an alternate parameter set
producing a real, attributable geometry change, structured errors for invalid requests, and process
stability across a valid→invalid→valid sequence. No UI existed yet — contract/protocol foundation
only. Gate: **PASS**. Full record: `docs/migration/BUILD-023-M1-PARAMETER-CONTRACT.md`,
`docs/migration/BUILD-023-M1-PARAMETER-DISCOVERY.md`.

## M2 outcome

A productive parameter panel (`desktop/frontend/src/parameter_panel.ts` and supporting modules)
covering all 16 `zerorod-parameters/v1` fields, grouped by the contract's own field-name semantics
(Project, Body, Rod & Groove, Strings, Channel, Tolerances) — not an invented taxonomy. Canonical
defaults loaded through the real `parameters_defaults` → `engine_parameters_defaults` path, never
duplicated in the frontend. Local draft state, dirty tracking, Reset, and local structural validation
(required/finite/positive-per-contract) — domain/cross-parameter rules deliberately left engine-only.
No automatic engine request on edit — M2 was local-editing foundation only. Gate: **PASS**. Human
Validation: **PASS** (Project Owner). Full record: `docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md`.

## M3 outcome

Apply became the first real trigger connecting the parameter draft to the engine: a valid, dirty
draft, when Applied, is sent through the exact M1 request path
(`requestPreviewMeshWithParameters` → `engine_preview_mesh_with_parameters` → the sidecar's
`preview` command) and the returned mesh atomically replaces the Three.js geometry — no backend
change was needed, since M1 had already built and tested the full parameterized path end to end.
Proved with the real productive pipeline: `body_width: 38 → 60 mm` measurably widened the rendered
model's X extent. Failure preserves the old geometry (fetch/validate happens before any scene
mutation). A metadata-only (`project_name`-only) Apply is accepted locally without an engine round
trip. Gate: **PASS**. Human Validation: **PASS** (Project Owner — "entered values change the real
ZeroRod model as expected"). Full record:
`docs/migration/BUILD-023-M3-PARAMETER-ENGINE-INTEGRATION.md`.

## M4 outcome

Editing a geometry-affecting field now schedules a debounced (300 ms) live-preview request on its
own — Apply remains, sharing the exact same request/commit pipeline rather than a second mechanism.
A new `live_preview.ts` module owns debounce, in-flight coalescing (only the latest superseded value
survives while a request is running), and generation-based stale-response protection (proven with a
directly-testable gate primitive, independent of whether the serialized sidecar could ever actually
reorder responses). `preview.ts` was split into `fetchPreview`/`commitPreview` so a request's result
is only ever committed to the visible scene if it's still the current desired generation. Camera
refit is now limited to the first load of a session and "extreme" bounding-box changes (>1.5×), so
small live edits no longer fight a user's manual framing. Gate: **PASS**. Human Validation: **PASS**
(Project Owner — live preview updates the model automatically, rapid edits/invalid-input
recovery/camera usability all confirmed). Full record: `docs/migration/BUILD-023-M4-LIVE-PREVIEW.md`.

## Final architecture behavior

```
canonical defaults (parameters_defaults)
    ↓
parameter panel populated (all 16 fields, grouped, unit-labeled)
    ↓
user edits a field
    ↓
local structural validation (required/finite/positive-per-contract)
    ↓
valid AND geometry-affecting?  →  debounced (300ms) schedule
    ↓                                  (metadata-only or invalid → no schedule)
persistent Python sidecar (reused across every request, lazy-started once)
    ↓
real ZeroRodCAD / CadQuery regeneration (zerorodcad.validation, then build_preview_scene)
    ↓
zerorod-mesh/v1
    ↓
generation still current?  →  Three.js geometry replacement (old geometry disposed first)
    (stale → discarded, scene untouched)
```

Apply performs the same flow immediately (skips the debounce wait), sharing the identical
generation-gated commit path — one pipeline, not two, throughout M3 and M4.

## Parameter contract (final)

`zerorod-parameters/v1`, unchanged since M1 (verified by diff against the M1 baseline commit
`2ac88d6`): 16 fields — `project_name` (metadata, string) plus 15 geometry fields (`body_width`,
`body_depth`, `fretboard_height`, `rod_diameter`, `groove_diameter`, `rod_center_z_offset`,
`groove_front_clearance`, `string_gauges_inch` (array, inch), `string_spacing`, `string_inlet_y`,
`string_inlet_z`, `channel_diameter`, `channel_overrun_at_inlet`, `channel_rod_clearance`,
`minimum_wall`), all mm except `string_gauges_inch`. Canonical defaults and domain validation remain
solely `zerorodcad.parameters`/`zerorodcad.validation` — never duplicated. `zerorod-sidecar/v1` and
`zerorod-mesh/v1` are both unchanged since Build 022/M1 — no protocol version bump anywhere in Build
023.

## Control coverage

All 16 fields represented: text input (`project_name`), 14 numeric text/decimal inputs, one ordered
per-entry gauge-array control (`string_gauges_inch`, add/remove, minimum one entry enforced). No
generic JSON editor, no sliders — deliberate CAD-precision choice.

## Live-preview strategy

Debounce: 300 ms, chosen from the measured warm engine round trip (~0.121–0.126 s, unchanged since
M1) plus normal desktop numeric-entry cadence. Stale-response protection: a monotonically increasing
generation counter (`createLatestWinsGate`), gating both the state-update callback and (critically)
the actual scene commit. Coalescing: while a request is in flight, further edits update a single
"queued" slot; only the latest survives once the in-flight request settles. Duplicate suppression:
editing back to the currently-represented value before the debounce fires cancels the pending
request entirely (0 requests); editing away and back after a value was already live-previewed issues
exactly one corrective request.

## Error behavior

Local (structural) invalidity: per-field message, `aria-invalid`, no automatic request; the last
valid preview is untouched. Domain-invalid (engine-rejected): structured error surfaced (field-level
where the engine provides `details.field`, form-level otherwise), the previous valid geometry is
never touched (the fetch/commit split guarantees this), and the sidecar itself survives to serve the
next request. Correcting the value clears the error automatically on the next successful settle.

## Camera behavior

Refit-to-bounds only on the session's first commit and on "extreme" bounding-box changes
(`isExtremeBoundsChange`, >1.5× largest-dimension change) — not on every live update. `OrbitControls`,
the scene, camera, and renderer are constructed once and never re-initialized; only the model
group's mesh/line children are disposed and replaced.

## Lifecycle

Unchanged from Build 022 M2 throughout Build 023: lazy sidecar start, persistent reuse across every
request (parameterless, parameterized, live-preview, or Apply-triggered — all the same process), a
detected crash or timeout triggers exactly one kill-and-restart retry, graceful shutdown with a
forced-kill fallback. Build 023 added no new lifecycle code — M1 proved the parameterized request
path fit the existing `engine::request` entry point without modification.

## Performance (final baseline)

- Sidecar cold start: ~0.635–0.645 s
- Warm median (parameterized `preview`): ~0.123–0.125 s
- Warm p95: ~0.127 s
- Debounce (fixed): 0.300 s
- Approximate perceived stable-edit → preview latency: ~0.42–0.43 s (debounce + engine round trip,
  reported separately per the M4 mandate, never blended into one misleading number)

No regression against the M1 baseline (~0.121–0.125 s) anywhere in M2-M4 — expected, since none of
M2-M4 changed backend code.

## Package size

Final M4 release measurement: 299,160,577 bytes / ~285.3 MiB / 201 files / 58 dirs / 77 symlinks /
160 Mach-O binaries — within noise of the Build 022 M4 baseline (285.21 MiB) and M3's own measurement
(also 299,160,577 bytes), since Build 023 added no new Python/Rust dependencies, only frontend
TypeScript/CSS.

## Dependency invariants

VTK: 0. PySide6: 0. Qt: 0. numba: 0. llvmlite: 0. scipy: 0. `cadquery-ocp-novtk` active;
`cadquery-ocp` (the VTK-bearing variant) absent. Reconfirmed fresh in every milestone's validation
gate, including this one's final rebuild.

## Security

Unchanged since Build 022: the WebView has no shell, process, or broad filesystem permission
(`core:default` only); Rust owns the sidecar process end-to-end; IPC is the private
`zerorod-sidecar/v1` stdin/stdout protocol; CSP stays
`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost`.
No new Tauri command was added after M1 — M2-M4 only added frontend call sites for commands M1 had
already built and tested.

## Human validation

| Milestone | Result | Source |
|---|---|---|
| M2 — Parameter Controls Foundation | **PASS** | Project Owner |
| M3 — Parameter-to-Engine Integration | **PASS** | Project Owner — "entered values change the real ZeroRod model as expected" |
| M4 — Live Preview Behavior & UX | **PASS** | Project Owner — live preview, rapid-edit stability, invalid-input recovery, camera/orbit usability, and normal operation all confirmed |
| M5 — Integration & Build Completion | **N/A** | M5 changed no runtime/product behavior — no additional human click-through required; the existing M2-M4 evidence stands |

## Known limitations

- `geometry_error` (Level 4 — a structurally/domain-valid parameter set that still fails at actual
  CadQuery solid construction) remains implemented but empirically untriggered — no known valid
  combination reaches it. Documented, not worked around with an artificial input (consistent with
  M1's own documented limitation).
- True out-of-order network/IPC response reordering was never observed against the real sidecar —
  by design, the frontend serializes dispatch. The stale-response invariant is proven at the
  `createLatestWinsGate` primitive level with controlled, manually out-of-order-resolved generations,
  exactly as the M4 mandate explicitly permits.
- `accepted` (the parameter state currently represented in the preview) is session-only; there is no
  project-file persistence to survive an app restart — that is explicitly Build 025 scope.
- The 1.5× camera-refit threshold is a simple, defensible starting point, not empirically tuned
  beyond the cases in `scene.test.ts`.

## Explicit non-scope (not part of Build 023)

STL export UI, STEP export UI, project persistence (open/save), full desktop feature parity,
settings, PySide6 retirement, signing/notarization. All remain explicitly later-build scope per
`docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md`'s migration strategy.

## Build 024 handoff

See `docs/migration/BUILD-024-HANDOFF.md` — **STL / STEP Export Workflow**, not started, requires
explicit Project Owner approval.
