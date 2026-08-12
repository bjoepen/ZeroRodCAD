# Build 023 / Milestone 2 — Parameter Controls Foundation

## Objective

Make the 16 `zerorod-parameters/v1` fields (established as contract in Build 023 M1) visible and
editable in the Desktop 2.0 WebView, with a local draft/dirty/reset lifecycle and local structural
validation — without connecting edits to engine regeneration. This is UI foundation for Build 023's
later milestones (parameter-to-engine integration, live preview), not those milestones themselves.

## Architecture

Four new frontend modules, each with a single responsibility, none of which talks to the sidecar
except the one explicitly allowed to (`parameters.ts`'s existing `fetchDefaultParameters`):

- **`parameter_metadata.ts`** — a single declarative table (`PARAMETER_FIELDS`) of UI-only
  presentation metadata (label, group, unit, control kind, `isMetadata`, `positiveOnly`,
  description) for each of the 16 canonical fields. Field names, units, and the `positiveOnly` flag
  are all copied verbatim from `docs/contracts/ZEROROD-PARAMETERS-V1.md`'s field table — this module
  invents no new field, no new default, no new range. `groupedParameterFields()` derives the
  render-order grouping from `GROUP_ORDER`.
- **`parameter_state.ts`** — pure, immutable draft-state logic: `draftFromValues()`,
  `updateScalarField()`, `updateGauge()`, `addGauge()`/`removeGauge()`, `isDraftDirty()`,
  `hasDraftErrors()`, `resetDraft()`, `serializeDraft()`. No DOM, no `invoke()` — fully unit-testable
  without a WebView.
- **`parameter_panel.ts`** — the DOM component. Builds the form once per successful defaults load,
  then mutates only the changed field's error text / the dirty badge / the Apply button per
  keystroke (never a full re-render), so typing never loses focus or cursor position. Wires
  `fetchDefaultParameters()` (M1's real defaults path) and nothing else from `parameters.ts` — no
  automatic call to `requestPreviewMeshWithParameters`.
- **`main.ts`** — adds a third `.parameters` column between the existing sidebar and viewport,
  instantiates `createParameterPanelController(parameterPanelEl)`, and calls `.load()` once at
  startup alongside the existing engine-status calls. No other change to `main.ts`'s existing
  status-panel/preview wiring.

This mirrors `preview.ts`'s existing pattern in the codebase (pure helper functions + a `create*Controller`
factory that owns DOM lifecycle) rather than introducing a new architecture or a form-handling
library — the stack stays plain TypeScript + Vite, per the mandate's dependency-arm requirement.

## Field coverage

All 16 fields from `docs/contracts/ZEROROD-PARAMETERS-V1.md` are represented, in contract order,
grouped as:

| Group | Fields |
|---|---|
| Project (metadata) | `project_name` |
| Body | `body_width`, `body_depth`, `fretboard_height` |
| Rod & Groove | `rod_diameter`, `groove_diameter`, `rod_center_z_offset`, `groove_front_clearance` |
| Strings | `string_gauges_inch`, `string_spacing`, `string_inlet_y`, `string_inlet_z` |
| Channel | `channel_diameter`, `channel_overrun_at_inlet`, `channel_rod_clearance` |
| Tolerances | `minimum_wall` |

Grouping follows the contract's own field-name prefixes (`body_`, `rod_`/`groove_`, `string_`,
`channel_`) — not an invented taxonomy (`parameter_metadata.test.ts` asserts every field is covered
exactly once and the group list matches).

## Units

`mm` for every geometry field except `string_gauges_inch`, which is `in` — exactly the contract's
unit column, shown next to each control. `project_name` has no unit. No unit conversion is performed
anywhere in M2.

## Control types

- `project_name`: text input.
- 14 numeric fields (`body_width` … `minimum_wall` minus `string_gauges_inch`): `<input type="text"
  inputmode="decimal">`, not `<input type="number">` — deliberately, to avoid the browser's own
  number-input value-sanitization (which silently discards invalid text like `"Infinity"` before
  JavaScript ever sees it) and to keep full control over exact decimal text, per the mandate's CAD
  precision requirement. No sliders.
- `string_gauges_inch`: one text input per array entry, in order, with an "Add gauge" button and a
  per-entry "Remove" button (disabled once only one entry remains — the contract requires at least
  one). No free-form JSON entry, no auto-sorting (order is engine-significant).

## Default loading

`main.ts` calls `parameterPanel.load()`, which calls `fetchDefaultParameters()`
(`parameters.ts`, unmodified from M1) → `invoke("engine_parameters_defaults")` → Rust's
`engine_parameters_defaults` command (unmodified from M1) → the sidecar's `parameters_defaults`
command → `zerorodcad.parameters.default_parameters()`. No default value is duplicated in the
frontend — the panel only ever renders what this call returns.

## Initial UI state

`load()` renders a `data-state="loading"` placeholder first, then either the populated form
(`data-state="ready"` on `.parameter-panel`) or a structured `data-state="error"` block showing the
engine error's `code`/`message` (never a raw exception) if the defaults call rejects.

## Local draft state and dirty tracking

`ParameterDraftState` tracks, per scalar field, the exact `raw` text currently in the control and
the last-known-valid `values` (a full `ZeroRodParametersValues`); gauges get a parallel
`rawGauges`/`gaugeErrors` pair. A field's `raw` always updates immediately; `values` only updates
when the new text parses cleanly, so `values` is always a contract-safe snapshot even mid-edit.

Dirty (`isDraftDirty`) compares every field's current `raw` text against the *formatted* loaded
baseline — deliberately including an in-progress invalid edit as "dirty," since the form no longer
reads as "matching what was loaded" even before the value is accepted. The dirty badge ("Unsaved
parameter changes") is purely a local-editing indicator in M2 — it does not imply Build 025 project
save semantics, which do not exist yet.

## Reset

"Reset to Defaults" calls `resetDraft(baseline)`, which is `draftFromValues` applied to the same
canonical default values the panel loaded — never a second hardcoded copy. All scalar inputs and the
gauge list are repopulated in place, all errors clear, and the dirty badge clears (`raw` again
exactly matches the formatted baseline).

## Local validation scope

`parameter_state.ts` validates only what the mandate scopes to the client:

- required (non-empty) text,
- numeric parse success, finiteness (`Number.isFinite`) — rejects non-numeric text, `NaN`,
  `Infinity`, `-Infinity`,
- the contract's own documented `> 0` constraint, for exactly the fields
  (`body_width`, `body_depth`, `fretboard_height`, `rod_diameter`, `groove_diameter`,
  `string_gauges_inch` entries, `channel_diameter`) whose contract row states it,
- at least one `string_gauges_inch` entry (enforced structurally — the UI never lets the count reach
  zero).

Cross-parameter/domain rules — groove-vs-rod, the string-spacing/`minimum_wall` feasibility formula,
the string-inlet tangent-clearance feasibility check — are **not** duplicated here. They stay
authoritative in `zerorodcad.validation.validate_parameters`, reachable (in M3+) through the
existing `invalid_parameters_domain` error path M1 already established.

## Validation feedback

An invalid field shows a concise, technical message next to that field (e.g. "Rod Diameter must be
greater than 0.") and sets `aria-invalid="true"` on its input; nothing else on the page changes,
there is no modal, and no raw JSON ever reaches the user. Correcting the value clears the message
and `aria-invalid` on the next keystroke that parses cleanly — no full-form reset required.

## Apply behavior (M2 semantics)

Per the mandate's preferred M2 semantics, Apply:

- validates the current draft (`serializeDraft`, which itself blocks on any field error or on a
  structural-shape failure),
- on success, **records** the resulting `ParametersRequest` (exposed as
  `controller.getAcceptedRequest()`) and shows "Applied locally. Preview regeneration is not yet
  connected — that begins in Build 023 M3.",
- on failure, shows a count of outstanding issues and changes nothing else,
- **never** calls `requestPreviewMeshWithParameters` or any other engine-facing command.

The Apply button itself is disabled whenever the draft currently has any error, so an invalid draft
cannot even be submitted through the UI; `parameter_panel.test.ts` additionally asserts that a
defensive click while errors are present still does not populate `getAcceptedRequest()`.

## Draft serialization

`serializeDraft()` returns `{ ok: true, request }` (a valid `zerorod-parameters/v1` envelope via the
existing `buildParametersRequest`) only when no field or gauge error is present *and*
`validateParametersShape()` (M1, reused unmodified) accepts the resulting values; otherwise
`{ ok: false, errors }`. `parameter_state.test.ts` and `parameter_panel.test.ts` both prove a draft
containing `NaN`/`Infinity`/a required-but-empty field can never produce a request — the invalid text
lives only in `raw`/`errors`, never in the serialized output.

## Preview behavior in M2

The existing Build 022 Three.js preview area is untouched — same `.viewport` element, same
`createPreviewController`, same "Load / Refresh ZeroRod" button. The panel shows a static hint
("Parameter changes are not yet applied to the preview until the next integration milestone.")
rather than presenting the gap as an error. `parameter_panel.test.ts`'s "no automatic preview IPC on
edit" test asserts the mocked `invoke()` is called exactly once (the initial defaults fetch) across a
sequence of scalar, `project_name`, gauge, and add-gauge edits — no `engine_preview_mesh` or
`engine_preview_mesh_with_parameters` call is ever triggered by editing.

## Metadata strategy

`project_name` is the only field with `isMetadata: true` in `parameter_metadata.ts`; it renders with
a small "metadata" badge next to its label and lives alone in the "Project" group, distinct from the
15 geometry-affecting fields. No behavioral difference exists yet in M2 (no regeneration exists at
all yet) — this is groundwork so M3/M4 can later skip regeneration for a metadata-only change.

## Accessibility baseline

Every control has an associated `<label for=…>` (or `aria-label` for the per-gauge inputs, which
share one visual group label), a native `<input>`/`<button>` element, `aria-describedby` linking each
scalar field to its error paragraph, and `aria-invalid` kept in sync with validation state. Buttons
and inputs get a visible `:focus-visible` outline (a new `--focus` token, defined for light and dark).
Grouping uses semantic `<fieldset>`/`<legend>`, not styled `<div>`s. This is a solid baseline, not a
full a11y audit — no automated a11y test tooling was added in M2.

## Tests

`parameter_metadata.test.ts` (field coverage, units, control kinds, grouping),
`parameter_state.test.ts` (draft mutations, dirty, reset, NaN/Infinity/required rejection, error
clearing, serialization valid/blocked), and `parameter_panel.test.ts` (jsdom-driven: loading/error
states, full field/unit rendering, editing → dirty, reset → clean, validation feedback and its
clearing, Apply recording an accepted request without any preview `invoke()` call, gauge add/remove)
— 59 new tests, on top of the 66 pre-existing frontend tests (125 total, all passing). No pixel
snapshots are used as evidence anywhere.

## Security

No new Tauri command, no new capability, no new filesystem or process access — the panel only calls
the M1-established `engine_parameters_defaults` command. CSP and the WebView's `core:default`-only
permission set are unchanged.

## Known limitations

- No live browser/GUI verification was performed in this environment (headless, no display) — the
  `docs/migration/BUILD-023-M2-HUMAN-VALIDATION.md` checklist is left for a human tester, per the
  mandate's own allowance for this.
- The Apply button's "accepted request" is not persisted anywhere (no Build 025 project-save
  target exists yet) — it is purely an in-memory record for this milestone and for M3 to build on.
- No cross-parameter feedback (groove-vs-rod, string-spacing/wall feasibility, channel-clearance
  feasibility) is shown client-side — by design; those stay engine-owned.

## Next milestone

**Build 023 / M3 — Parameter-to-Engine Integration**: connect Apply (or a successor action) to
`requestPreviewMeshWithParameters`, decide the live-update UX (debounce vs. explicit trigger), and
surface engine-side (`invalid_parameters_domain`/`geometry_error`) errors back onto individual
fields using the `aria-invalid`/error-paragraph plumbing this milestone already built. Not started
by this milestone.
