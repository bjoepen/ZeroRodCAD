# Build 023 / Milestone 3 — Parameter-to-Engine Integration

## Objective

Connect the M2 parameter panel to the real ZeroRodCAD engine: pressing **Apply** on a valid, dirty
parameter draft now actually regenerates the CAD geometry through the productive
Tauri → Rust → persistent Python sidecar → ZeroRodCAD → CadQuery pipeline and replaces the
rendered Three.js mesh — the first Build 023 milestone in which editing parameters from the new
desktop UI changes real geometry. M1 established what the parameters mean, M2 made them editable,
M3 establishes causality: nothing regenerates until the user deliberately presses Apply.

## M2 human validation result

Reported directly by the Project Owner: **PASS**, against the M2 release artifact (commit
`d691d95`). See `docs/migration/BUILD-023-M2-HUMAN-VALIDATION.md` for the updated record — no
additional or repeat validation was performed to produce that record; it documents what was
reported, not a re-test.

## Architecture

M3 required **no backend changes**. `src/zerorod_sidecar/main.py`'s `_run_preview_command` already
accepted and used a non-empty `parameters` object end to end (Level 1–4 validation, real geometry
construction) since Build 023 M1; `desktop/src-tauri/src/commands.rs`'s
`engine_preview_mesh_with_parameters` and `desktop/frontend/src/parameters.ts`'s
`requestPreviewMeshWithParameters` were already wired and tested in M1, just never called from any
UI. M3 is the first thing that actually calls them. `zerorod-parameters/v1`, `zerorod-mesh/v1`, and
`zerorod-sidecar/v1` are all unchanged — reused exactly as M1 defined them (§11/§41 of the mandate).

Three frontend files changed:

- **`parameter_state.ts`**: two new pure exports — `cloneValues` (was already private, now shared)
  and `isGeometryUnchanged(a, b)`, which compares every field except `project_name` for the
  metadata-only-Apply optimization below. `isDraftDirty` itself is unchanged; only what
  `parameter_panel.ts` passes as its `baseline` argument changes (see "Dirty state" below).
- **`preview.ts`**: `load()` now takes an optional `values?: Partial<ZeroRodParametersValues>` and
  calls `requestPreviewMeshWithParameters(values)` instead of `requestPreviewMesh()` when given.
  Same scene, same camera/controls, same geometry-replacement code path for both — no second
  Three.js scene, no renderer re-initialization. `load()` now also returns
  `{ ok: boolean; error?: unknown }` so a caller can react to success/failure without re-parsing the
  status-callback text.
- **`parameter_panel.ts`**: `createParameterPanelController` now takes a second argument,
  `applyParameters: (values) => Promise<{ ok; error? }>` — main.ts wires `preview.load` directly
  (its optional-parameter signature is structurally compatible). The panel never imports or calls
  anything sidecar-facing itself; it only asks its caller to do so, mirroring how `preview.ts`
  itself takes an `onStateChange` callback instead of owning status-panel DOM.

`main.ts`'s only change: `createParameterPanelController(parameterPanelEl, preview.load)` and an
updated subtitle/hint string. `desktop/frontend/src/parameter_metadata.ts` is unchanged.

## Apply workflow

```
edit (draft only, no request)
    ↓
local validation (parameter_state.ts, unchanged from M2)
    ↓
user presses Apply
    ↓
guard: not already applying, draft has no errors, draft differs from accepted, shape-serializable
    ↓
snapshot the values being submitted (cloneValues — immune to concurrent edits mid-flight)
    ↓
geometry-unchanged? (§24) → accept locally, no engine call
    ↓ (else)
preview.load(values) → requestPreviewMeshWithParameters → Rust engine_preview_mesh_with_parameters
    → sidecar preview command (parse → validate_parameters → build_preview_scene → zerorod-mesh/v1)
    ↓
success: mesh validated, old Three.js geometry disposed and replaced, camera refit
    ↓
accepted := submitted snapshot, dirty clears, "Applied — preview updated." shown
    (failure: accepted/draft/preview all untouched, dirty stays true, error shown)
```

Apply is the *only* trigger. No `input`, `change`, `blur`, gauge add/remove, or Reset call
`applyParameters` — verified by `parameter_panel.test.ts`'s "editing never triggers a request"
suite, which edits every kind of field plus adds a gauge and asserts zero calls.

## State model

- **`draft`** (`parameter_state.ts`, unchanged shape from M2): what's currently in the form,
  including in-progress invalid text.
- **`accepted`** (new in M3): the last parameter set the *application* has actually accepted —
  either because the engine returned a successful mesh for it, or (metadata-only case) because it
  was locally accepted without needing the engine. Starts equal to the canonical defaults on load.
  Session-only — no project-file persistence exists yet (Build 025), so `accepted` does not survive
  an app restart.
- **`defaults`** (new in M3, split out from what M2 called `baseline`): the canonical default set
  from `parameters_defaults`, used *only* as Reset's target. Kept deliberately separate from
  `accepted` so Reset and "what Apply compares against" can disagree — see "Reset semantics" below.
- **Dirty**: `isDraftDirty(draft, accepted)` — redefined from M2's "differs from loaded defaults" to
  M3's "differs from the last accepted state" (§26 of the mandate). The function itself didn't
  change; only which value M3's caller passes as the comparison baseline did.
- **`applyStatus`**: `"idle" | "applying" | "applied" | "error"`. Set to `"applying"` synchronously,
  before any `await`, so no interleaved second Apply can start (see "Concurrency" below). A fresh
  edit after a settled `"applied"`/`"error"` resets it to `"idle"` and clears the stale outcome
  message — otherwise a leftover "Applied" banner would sit next to a draft the user has since
  changed again.

## Concurrency / exactly-one-request-per-Apply

`handleApply`'s guard checks and the `applyStatus = "applying"` assignment all run synchronously
before the function's first `await`. JavaScript runs that prefix to completion without yielding, so
a second click (or a defensively-forced call while the button is disabled) cannot interleave between
the guard check and the flag being set — `parameter_panel.test.ts`'s "blocks a second Apply while
one is already in flight" test proves this with a manually-controlled un-resolved promise and two
rapid clicks, asserting exactly one call to `applyParameters`. The Apply button is also disabled for
the duration (`applyButtonEl.disabled = applying`), and Reset is disabled too, so the user cannot
mutate `draft` out from under the in-flight request's already-captured value snapshot while waiting.

## Enter key

No submit-type button exists in the form (both Reset and Apply are `type="button"`), so per the
HTML form-submission algorithm there is no implicit-submission target — pressing Enter in a text
field does nothing (§38 of the mandate: a deliberate "no request" choice, not an oversight).
`parameter_panel.test.ts` asserts a `keydown`/`Enter` dispatch never calls `applyParameters`.

## Metadata-only Apply (project_name)

`isGeometryUnchanged(submittedValues, accepted)` compares every field except `project_name`. If it
returns `true` — i.e., only `project_name` (or nothing) actually differs — Apply accepts the new
state locally and shows "Applied locally — metadata only, no geometry regeneration needed." without
ever calling `applyParameters`/the engine. This required no protocol change and no new backend
command: it's a purely client-side comparison against the already-tracked `accepted` state (§24 of
the mandate explicitly allows this only "wenn dies mit der bestehenden State-Architektur sauber
möglich ist" — it was, so no new abstraction was built beyond this one comparison function).

## Reset semantics (redefined for M3's accepted-state model)

Reset still only ever touches the local draft (never calls `applyParameters` — §25). It restores the
*canonical defaults* into the draft, not into `accepted`. Consequences, both proven by
`parameter_panel.test.ts`:

- If `accepted` already equals the defaults (nothing has been successfully Applied to something
  else yet), Reset leaves dirty `false`.
- If `accepted` currently differs from the defaults (some other state was already Applied), Reset
  makes the draft show the defaults again but dirty becomes/stays `true`, because the draft (now
  defaults) differs from `accepted` (still the previously-applied state) — the user must press Apply
  again to actually make the engine/preview reflect the defaults. This is the M3-specific behavior
  the mandate calls "more important than the simplified M2 rule" (§25).

## Real geometry proof

`body_width: 38 → 60 mm` (M1's own proven alternate case) is exercised through the real productive
pipeline in `scripts/validate-build023-m3.sh`'s real-integration section: two live requests against
the freshly rebuilt onedir sidecar binary, asserting the returned mesh's X bounds extent grows from
~38 mm to ~60 mm — the same evidence class M1 already established, now proven reachable from the
Apply code path's exact request shape rather than only from a hand-built JSON line.

## Atomic preview replacement / failure handling

Unchanged from M2/M3's `preview.ts`: `requestPreviewMeshWithParameters` is awaited and its result
passed through `meshContractToGeometries` (which validates and throws on a bad payload) *before*
`clearGroup(modelGroup)` ever runs. A failed or invalid request therefore never reaches the
geometry-clearing step — the previously rendered model, camera, `OrbitControls`, and renderer are
completely untouched. This ordering already existed in Build 022 M3 and needed no change for M3;
`parameter_panel.ts`'s own `accepted`/`draft`/dirty state additionally stays untouched on failure
(proven by the "failed Apply preserves accepted state and keeps dirty true" test).

## Renderer / camera / OrbitControls

`fitCameraToBounds()` runs after every successful load, parameterized or not — unchanged M2/M3
behavior, reused as-is (§22 of the mandate explicitly accepts "refit after successful Apply" rather
than a new camera-preservation policy). `OrbitControls`, the scene, and the renderer are constructed
once by `createScene` and never touched again by `load()` — only the mesh/line children of
`modelGroup` are disposed and replaced, so rotate/zoom continue working after every Apply with no
re-initialization or duplicate event listeners.

## Lifecycle / sidecar failure / timeout

All unchanged from Build 022 M2's `engine.rs`: the persistent sidecar is reused across every Apply
request; on a detected crash or timeout, `engine::request` kills the dead process and retries
exactly once against a freshly spawned one before surfacing a structured error. From
`parameter_panel.ts`'s perspective this is invisible — `applyParameters` either eventually resolves
`{ ok: true }` or `{ ok: false, error }`; the panel doesn't know or care whether a retry happened
underneath. The existing 30 s `REQUEST_TIMEOUT_SECS` is unchanged; M3 introduces no UI-configurable
timeout.

## Performance / memory

Measured in `scripts/validate-build023-m3.sh` against the freshly rebuilt onedir sidecar (same
methodology as M1's own measurement): default and alternate (`body_width: 60`) explicit-parameter
`preview` requests, plus a 20-request repeated-Apply sequence checking sidecar RSS growth and orphan
processes. See the script's own output for the exact numbers reproduced at validation time; no
regression beyond M1's baseline (~0.121–0.123 s warm median) is expected, since M3 adds no new
backend code on the request path — only a UI call site that was already fully built and tested in
M1.

## Security

Unchanged. No new Tauri command, no new capability, no new filesystem/process access. Apply still
only ever calls the M1-established `engine_preview_mesh_with_parameters` (already registered,
already capability-scoped identically to `engine_preview_mesh`).

## Known limitations

- `geometry_error` (Level 4) is still not empirically triggerable by any known valid-but-unbuildable
  parameter combination — same limitation M1 documented; M3 does not invent an artificial trigger,
  per the mandate's explicit instruction not to.
- No live browser/GUI verification was performed in this environment (headless, no display) — see
  `docs/migration/BUILD-023-M3-HUMAN-VALIDATION.md`, left pending for the Project Owner.
- `accepted` is session-only; there is no project-file persistence (Build 025) to survive an app
  restart.
- The metadata-only-Apply optimization only recognizes "nothing outside `project_name` changed" —
  it does not attempt any finer-grained per-field diffing of *which* geometry field changed, since
  the engine's `preview` command always regenerates the full mesh from a complete value set anyway.

## Next milestone

**Build 023 / M4 — Live Preview Behavior & UX**: automatic/debounced regeneration, if approved.
Requires explicit Project Owner approval after this milestone's human validation — not started here.
