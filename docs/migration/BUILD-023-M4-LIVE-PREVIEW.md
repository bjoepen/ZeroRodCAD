# Build 023 / Milestone 4 — Live Preview Behavior & UX

## Objective

Turn the M3-proven manual `Apply → real geometry` pipeline into an automatic, debounced live
preview: a valid geometry edit now regenerates the Three.js model on its own, a short moment after
the user stops typing, without the accelerator (regeneration) ever firing before the steering wheel
(validation) is ready. Apply remains, but its semantics change to share the exact same pipeline and
stale-response protection as the automatic path, rather than being a second, separate mechanism.

## M3 human validation result

Reported directly by the Project Owner: **PASS** — "Eingegebene Werte verändern das reale
ZeroRod-Modell entsprechend den Erwartungen" (entered values change the real ZeroRod model as
expected). See `docs/migration/BUILD-023-M3-HUMAN-VALIDATION.md` for the updated record. No
additional or repeat validation was performed to produce that record.

## Architecture — one pipeline

No backend change was needed (same as M3): the sidecar's `preview` command, the Rust
`engine_preview_mesh_with_parameters` command, and `zerorod-parameters/v1` were already complete as
of M1. M4 is entirely a frontend scheduling/UX layer on top of the same request path M3 already
proved. Two new modules, three modified ones:

- **`live_preview.ts`** (new) — the debounce/coalescing/stale-response-protection engine, generic
  over the scheduled value type and the request's success payload type. Two exports:
  - `createLatestWinsGate()`: the minimal stale-response primitive (§13 of the mandate) — a
    monotonically increasing generation counter where only the most-recently-issued generation is
    ever "current." Directly unit-tested with manually out-of-order resolution
    (`live_preview.test.ts`), independent of whether the real transport could ever actually reorder
    responses.
  - `createLivePreviewController()`: debounce timer + in-flight tracking + superseded-value
    coalescing, built on the gate above. Exposes `schedule` (debounced), `scheduleImmediate`
    (Apply's flush-now path), `cancelPending`, and `dispose`.
- **`scene.ts`** (extended) — `isExtremeBoundsChange(previous, next, ratio = 1.5)`: the pure
  camera-refit heuristic (see "Camera behavior" below).
- **`preview.ts`** (restructured) — `load()` is now built from two exported halves:
  `fetchPreview()` (network/IPC round trip + mesh validation/conversion, no scene mutation) and
  `commitPreview()` (synchronous scene replacement + camera-refit decision + status callback).
  `load()` itself (fetch immediately followed by unconditional commit) is unchanged in behavior and
  still serves the manual "Load / Refresh ZeroRod" button. The fetch/commit split is what lets the
  live-preview controller gate scene mutation on "is this result still current" before ever calling
  `commitPreview`.
- **`parameter_state.ts`** (extended) — `valuesEqual()`, a full field-for-field equality check
  (including `project_name`), used as the live-preview controller's dedup comparison.
- **`parameter_panel.ts`** (rewritten) — owns the actual `LivePreviewController` instance, wires
  every draft mutation through one function (`reconcileLivePreview`), and Apply through
  `scheduleImmediate` on the same instance.

## Concurrency model — why "out of order" is tested at the gate, not the controller

`createLivePreviewController` never dispatches two requests at once: while one is in flight, further
`schedule()`/`scheduleImmediate()` calls only update a single "queued" slot (last write wins), and
the next request only starts once the current one settles. This is a deliberate choice — it
minimizes engine load (§33 of the mandate) and avoids ever sending a request for an
already-superseded draft. One consequence: under this design, `createLivePreviewController` itself
can never observe a truly out-of-order response through normal `schedule()` calls, because nothing
can complete "later" than something that hasn't started yet.

The mandate's §24 out-of-order test is therefore proven at the right level: `createLatestWinsGate`
directly, with manually controlled generation issuance and resolution order
(`live_preview.test.ts`'s "discards an earlier generation once a later one has been issued,
regardless of resolution order" test) — exactly what the mandate explicitly permits ("Real engine
requests need not naturally return out of order for the race invariant to be tested"). The
controller then *uses* that gate internally for every dispatch, so the invariant holds end to end
even though it's not separately re-exercised via genuine concurrency at the controller level.

## Debounce value and rationale

**300 ms** (`LIVE_PREVIEW_DEBOUNCE_MS` in `parameter_panel.ts`). Chosen from:

- the measured warm engine round trip, unchanged since M1/M2/M3: ~0.121–0.126 s.
- normal desktop numeric-entry cadence: a continuous edit ("38" → "4" → "45" → "6" → "60") needs to
  collapse into one request, not five — 300 ms comfortably exceeds typical inter-keystroke gaps
  while typing a short number.
- the mandate's own candidate range (250–350 ms) and worked example (debounce ~300 ms + engine
  ~125 ms ≈ total ~425 ms stable-edit-to-preview latency) — this milestone's actual measured total
  (see "Performance" below) lands almost exactly there.

## Request scheduling — the one reconciliation function

Every draft-mutating handler (`handleScalarInput`, `handleGaugeInput`, `handleAddGauge`,
`handleRemoveGauge`, `handleReset`) ends by calling a single `reconcileLivePreview()`:

1. If the draft currently has any local validation error (any field, not just the one just edited)
   → cancel any pending debounce, schedule nothing (§9 of the mandate: the whole draft must be
   structurally valid and serializable before any automatic request can exist).
2. Else if the draft's geometry-affecting fields are unchanged from `accepted` (a pure metadata edit,
   or an edit that returned to the already-represented value) → cancel any pending debounce,
   schedule nothing.
3. Else → mark status `"pending"` and call `livePreview.schedule(draft.values)`.

This one function, reused unconditionally, is what naturally produces every specific behavior the
mandate calls out by name — no per-field special-casing was needed:

- **Rapid edits collapse** (§11/§23): each new `schedule()` call resets the debounce timer.
- **"38 → 40 → back to 38 before the debounce fires" issues zero requests** (§36): the controller's
  own dedup compares against `targetValue` (whatever was last dispatched/queued), which is still 38
  at that point.
- **"40 already previewed, then back to 38" issues exactly one request**: `targetValue` is now 40,
  so scheduling 38 is recognized as a real change.
- **A pending request is cancelled if the draft becomes invalid for any reason** — even if the
  invalid field isn't the geometry field that was pending — because step 1 checks the *whole* draft.
- **A concurrent metadata edit while a geometry request is pending does not cancel it** — step 2's
  `isGeometryUnchanged` check compares against `accepted`, not against what's merely pending, so a
  still-geometry-different draft continues to (re)schedule normally even if `project_name` also
  changed in the same edit.

## State semantics (§17/§18 of the mandate — a deliberate choice, not an accident)

M3 had `draft` and `accepted`. Rather than introduce a third `previewed` concept, M4 **merges**
"previewed" into `accepted`: since every successful engine round trip (live-triggered or
Apply-triggered) now goes through the same `onSettle` callback, `accepted` means "the parameter
values currently represented in the preview, or the last state a completed round trip (or a
metadata-only local accept) confirmed." `defaults` (canonical default values) stays separate, used
only as Reset's target — unchanged from M3.

Dirty (`isDraftDirty(draft, accepted)`, unchanged function from M2/M3) stays meaningful under this
model: it now reads as "the draft hasn't been reflected in the preview yet" — true while debouncing,
while invalid, or while the last attempt errored; false once a live update or Apply succeeds. This
is a narrower, more literal meaning than M3's "you haven't clicked Apply yet," but it is not
meaningless — it directly answers "does what I'm looking at match what I typed."

## Apply semantics (§16/§22)

Apply is enabled exactly when the draft is locally valid and dirty (same condition as M3, now
evaluated against the live-preview-updated `accepted`). Clicking it:

- for a metadata-only change: accepts locally, identical to M3, no engine call.
- for a geometry change: calls `livePreview.scheduleImmediate(draft.values)` — cancels any pending
  debounce and dispatches right away (still subject to in-flight coalescing), then returns
  immediately; the shared `onSettle` callback (same one live preview uses) does all the resulting
  state updates. No separate async code path, no separate error formatting.

Because `accepted` is not updated on a failed attempt, Apply stays *enabled* after an error even
though nothing in the draft has changed — this is what makes Apply a genuine manual retry tool
(§16's "useful while live preview state is pending/error"), not just a redundant "do the same thing
sooner" button.

## Reset semantics (§19 — a deliberate change from M3)

Reset now only ever mutates the local draft, then calls the same `reconcileLivePreview()` every
other edit uses — no immediate dispatch, no special-cased forced refit. If `accepted` already equals
the defaults, the scheduler's own dedup means literally nothing is requested. If `accepted` differs
(some other state had been live-previewed or Applied), Reset makes the draft show the defaults
again, and the normal debounce/schedule path takes it from there — the default geometry "appears
automatically" a debounce-interval later, exactly as §19 describes, without any Reset-specific
branch in the scheduling logic.

## Metadata (`project_name`)

Unchanged in spirit from M3, verified explicitly for M4: editing `project_name` alone never calls
`reconcileLivePreview`'s scheduling branch (`isGeometryUnchanged` against `accepted` is true), so it
never reaches `livePreview.schedule`/`fetchPreview`. It still requires an explicit Apply to become
part of `accepted` — M4 didn't change *when* metadata gets accepted, only added the guarantee that a
concurrent geometry edit's pending request survives a metadata edit alongside it.

## Invalid input / domain-error UX

Local (structural) invalidity: the existing per-field error text/aria-invalid from M2/M3 is
unchanged; `reconcileLivePreview` additionally ensures no automatic request exists while any field
is invalid, and the live-status line is left showing whatever it last legitimately showed (not
forced to a generic "invalid" state) — the per-field messages are the primary signal for that case.

Domain-invalid (structurally fine, rejected by the engine): the live-status line shows
`"Could not update preview: <message>"`, any `details.field`-associated message is also shown next
to that field, and — because of `fetchPreview`/`commitPreview`'s split — `commitPreview` is simply
never called, so the previously rendered geometry is left completely untouched. Correcting the value
clears the error the next time a request succeeds (the status line only changes on the next
`onRequestStart`/`onSettle`, exactly mirroring M2/M3's "error clears on correction" pattern one
level up).

## Live-preview status vocabulary (§27/§28)

One persistent status line (`.parameter-live-status`, replacing M3's separate dirty badge and
apply-outcome message) cycles through four states: `up-to-date`, `pending`, `updating`, `error`.
`data-status` is always updated synchronously (so tests and any future a11y tooling see the true
state immediately); the *text* specifically for `updating` is delayed by 150 ms
(`UPDATING_DISPLAY_DELAY_MS`) — since the measured warm engine round trip (~125 ms) is usually
faster than that, the common case never shows "Updating preview…" at all, avoiding the flicker §28
warns about. A slower-than-usual request still becomes visible once the delay elapses.

## Camera behavior (§29 — a central human-validation point)

`commitPreview` (in `preview.ts`) now only refits the camera when either:

- this is the very first commit of the session (`hasCommittedOnce` is false), or
- the model's bounding box changed "extremely" — `scene.ts`'s `isExtremeBoundsChange(previous, next,
  ratio = 1.5)`, true when the largest dimension grew or shrank by more than 50%.

This applies uniformly to the manual button, live preview, and Apply, since all three now call the
same `commitPreview`. A small edit (e.g. 38 mm → 39 mm) does not refit at all, preserving whatever
zoom/rotation the user set; a large jump (e.g. defaults → 3× the body width) does. This is a
deliberately simple, directly testable heuristic (`scene.test.ts`) rather than a larger
camera-preservation policy engine, per the mandate's explicit restraint ("controlled refit/fallback,"
not a new policy subsystem). `OrbitControls`, the scene, camera, and renderer instances are
untouched by any of this — only `modelGroup`'s children are disposed and replaced.

## Renderer / resource safety

Unchanged disposal path from M2/M3 (`clearGroup`, already tested in `scene.test.ts`): every
`commitPreview` call disposes the previous mesh/line geometry and materials before adding new ones.
Repeated live updates therefore cannot accumulate GPU resources. `parameter_panel.test.ts`'s
100-iteration repeated-Apply-cycle test exercises the scheduling/state layer at that volume (mocked
`commitPreview`); the actual disposal correctness is proven once, structurally, in `scene.test.ts`
rather than 100 times redundantly.

## Real pipeline proof

`scripts/validate-build023-m4.sh` proves the same `body_width: 38 → 60 mm` case M1/M3 already
proved, plus a sequential 38→45→60→38 sequence and a gauge change, through the real freshly rebuilt
sidecar, and reuses TE-002.1's `benchmark_sidecar_runtime.py` for a 20-request RSS/timing check —
see the script's own output for the exact numbers reproduced at validation time.

## Performance

Perceived latency is reported as two separate numbers, not blended (§49 of the mandate):
debounce (300 ms, fixed) + measured warm engine round trip (~0.12–0.13 s, unchanged since M1) ≈
~420–430 ms stable-edit-to-preview total. No engine-side change exists to regress; the only new
frontend cost is the debounce/scheduling bookkeeping itself, which is negligible (plain
`setTimeout`/closure state, no heavy computation).

## Security

Unchanged. No new Tauri command, no new capability. Live preview and Apply both still only ever call
the M1-established `engine_preview_mesh_with_parameters`/`engine_parameters_defaults` commands.

## Known limitations

- No live browser/GUI verification was performed in this environment (headless, no display) — see
  `docs/migration/BUILD-023-M4-HUMAN-VALIDATION.md`, left pending for the Project Owner. Camera
  preservation UX in particular (§29) needs a human's actual sense of "does this feel right," which
  no unit test can substitute for.
- `isExtremeBoundsChange`'s 1.5x threshold is a simple, defensible starting point, not empirically
  tuned against real ZeroRod parameter ranges beyond the examples in `scene.test.ts` — a reasonable
  target for UX refinement if human validation finds it too eager or too reluctant to refit.
- Real concurrent request reordering was not (and structurally cannot be, by this design) observed
  against the actual sidecar — see "Concurrency model" above for why the gate-level test is the
  correct evidence for this invariant.

## Next milestone

**Build 023 / M5 — Integration & Build Completion**, per the roadmap's provisional sequence. Not
started by this milestone — requires explicit Project Owner approval after M4 human validation.
