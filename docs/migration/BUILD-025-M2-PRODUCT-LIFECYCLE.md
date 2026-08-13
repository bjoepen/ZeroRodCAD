# Build 025 / Milestone 2 — Product UI Productization & Lifecycle Polish

Engineering record. Turns the technically-grown Tauri shell into a normal desktop application:
automatic initial preview (closing the "empty viewport at first launch" gap Discovery identified),
relocation of development/debug controls out of the main product UI into a new Diagnostics view,
and a friendly startup-failure/Retry surface — all without any new engine, protocol, or process
architecture (`engine.rs`'s lazy-spawn/timeout/crash-restart machinery is unchanged, confirmed by
`git diff --quiet` in the validation gate).

## Baseline

- Build 025 M1: `feature/build025-m1-project-persistence`, final commit `d3c93b9` (the native-close
  corrective fix) — Gate `BUILD-025-M1 CONSISTENCY GATE: PASS`, Human Validation PASS.
- This milestone: `feature/build025-m2-product-lifecycle`, branched from `d3c93b9`.

## Analysis — verified against source, not assumed from Discovery

`docs/migration/BUILD-025-LIFECYCLE-ANALYSIS.md` (Discovery, pre-M2) already established, and this
milestone re-confirmed directly against the actual M1 code before changing anything:

1. **The sidecar already auto-starts.** `parameterPanel.load()`'s `fetchDefaultParameters()` call
   (`parameters_defaults` → `engine_parameters_defaults` → `engine::request()` →
   `ensure_started()`) is the first real IPC round trip on every app launch, and it already lazily
   spawns the sidecar — confirmed unchanged in `engine.rs`. The mandate's "no manual engine start"
   principle was **already substantially met at the process level** before this milestone.
2. **The actual gap was the preview, not the engine.** Nothing in the pre-M2 `init()` ever called a
   preview-fetching function — the user had to click "Load / Refresh ZeroRod" to see a model at
   all. This is the one concrete lifecycle behavior this milestone changes.
3. **Five controls didn't belong in the main product UI**: the 5-row technical status panel,
   "Start / Check Engine", "Ping Engine", "Request Preview Data", and the raw "last action" log —
   see Lifecycle Analysis §2/§3 for the full per-control rationale. "Load / Refresh ZeroRod" is
   different: its *capability* (fetch + render the model) is genuinely needed, just not as a manual
   click once the automatic initial preview exists; a manual Reset/Fit View replacement is
   explicitly Build 025 M3 scope, not built here (mandate §2).

## Automatic initial preview (§10-13/§41 of the mandate)

**Design decision: extend `parameter_panel.ts`'s own `load()`, not build a second preview
pipeline.** `load()` already fetches canonical defaults and calls `buildForm(values, values)`,
which sets `accepted`. It now performs one additional step in the same function, after `buildForm`
succeeds: `previewIO.fetchPreview(values)` → on success, `previewIO.commitPreview(data)` — the
exact same `fetchPreview`/`commitPreview` pair `loadProjectValues` and the live-preview scheduler
already use (`live_preview.ts`). No new pipeline, no new semantics for `accepted`/`draft`/preview
consistency (§12): the initial preview is committed through the identical path a live-preview edit
or Apply would use, so nothing downstream needs to know it was "the automatic one."

`load()`'s return type changed from `Promise<void>` to a small discriminated result,
`ParameterPanelLoadResult`:

```ts
type ParameterPanelLoadResult =
  | { ok: true }
  | { ok: false; stage: "defaults" | "preview"; error: unknown };
```

This distinguishes a `parameters_defaults` failure (before any form existed — parameter_panel.ts's
own existing inline `renderLoadError` still handles the visible detail) from an initial-preview
fetch failure for those same, always-domain-valid canonical values. The latter is structurally an
engine/sidecar-level failure (a crash or timeout between the two round trips — the same
crash-restart-once machinery `engine.rs` already has can legitimately still fail on both attempts),
never a domain-validation error, so it is reported distinctly rather than folded into the ordinary
live-preview inline-error surface (§27/§28: domain errors stay local; this is not one).

**Exactly-once (§11):** `load()` is called from exactly one place — `startup.ts`'s `start()`,
itself called exactly once from `main.ts`'s top level (`void startup.start();`). Retry re-invokes
`start()` (see below), which re-invokes `load()` — never a second, parallel call.

## Startup coordinator (`startup.ts`, §54 of the mandate)

A small, dedicated module — not stacked into `main.ts` — owning only the startup *presentation*:

- **Anti-flicker (§20/§48):** "Preparing ZeroRodCAD…" only renders if `io.run()` (wired to
  `parameterPanel.load()`) is still pending after 250ms — the same delayed-indicator idea
  `parameter_panel.ts`'s own `UPDATING_DISPLAY_DELAY_MS` already established for live preview,
  reused rather than reinvented.
- **No "ready" banner (§21):** on success, the container is simply cleared. A normal product app
  signals ready by working, not by announcing it.
- **Startup failure UX (§13/§24-27, from Lifecycle Analysis §5's design):** a plain-language
  message ("ZeroRodCAD's engine could not start." / "ZeroRodCAD could not load the initial
  model.", chosen by `stage`) with **Retry** (re-invokes the identical `start()` sequence, so it
  reuses the correct `EngineManager` lifecycle rather than the frontend spawning anything — §25)
  and **Show Details** (reveals the sanitized `code: message` — never a raw traceback, matching
  every other error surface in this app). No redundant Quit button — quitting is already covered
  by the app's normal window controls (§24).

## Diagnostics view (`diagnostics_panel.ts`, §16-18/§37/§38 of the mandate)

Relocates, rather than deletes, the genuine diagnostic value of the removed controls: build/version
identity (`app_info`), engine status including pid and last error (`engine_status`), and
Python/CadQuery/OCP version info (`engine_sidecar_status`) — the exact three existing, read-only
Tauri commands already used by the removed controls, reused unmodified. Also surfaces the two real
protocol identifiers already defined in the frontend (`PARAMETERS_SCHEMA`/`MESH_SCHEMA` from
`parameters.ts`/`mesh.ts`) rather than inventing a new "protocol version" field or Rust/sidecar
endpoint.

A small toggle button shows/hides an inline section — deliberately not a modal dialog (avoids any
focus-trap risk, §55) and deliberately not wired into a menu (§37 — Build 025 M4's job once native
menus exist; this is what a future Help-menu item will eventually open). The only action is
"Refresh Status" (re-fetches all three); there is no kill-sidecar, start-python, or raw-IPC action
(§17) — the classification is deliberate per control, not "move every old debug button."

Opening, closing, and refreshing never call a preview/project/export/dirty-affecting command (§38)
— verified both by inspection (only the three read-only status fetchers are imported) and by a
dedicated test asserting no such call happens across open/refresh.

## Technical-controls removal (§14/§15, classification from Lifecycle Analysis §3)

| Control | Classification | Disposition |
|---|---|---|
| 5-row status panel | `MOVE_TO_DIAGNOSTICS` | Content now in Diagnostics (app/engine/python/cadquery/ocp/protocol rows) |
| "Start / Check Engine" | `REMOVE_FROM_PRODUCT_UI` | Removed outright — redundant once the engine auto-starts and the initial preview auto-loads |
| "Ping Engine" | `MOVE_TO_DIAGNOSTICS` | Its sidecar-version output is now part of Diagnostics's status fetch |
| "Request Preview Data" | `REMOVE_FROM_PRODUCT_UI` | Removed outright — self-documented as non-rendering, superseded by automatic initial preview |
| "Load / Refresh ZeroRod" | Superseded, not redesigned | Its capability (fetch + render) is now automatic; a manual Reset/Fit View replacement is explicitly Build 025 M3 scope, not built here |
| "last action" raw log | `MOVE_TO_DIAGNOSTICS` (subsumed) | Superseded by Diagnostics's structured rows; no raw JSON log carried forward — nothing in Diagnostics needs it, and the mandate's "no raw JSON" goal (§18) argues against reintroducing one |

`main.ts` now wires exactly four panels — Project, Parameters, Export, Diagnostics — plus the
startup coordinator and the (unchanged) `onCloseRequested`/`beforeunload` lifecycle wiring.

## Known Quit/⌘Q limitation — unchanged, not addressed here (§3/§32/§64 of the mandate)

The default macOS "Quit" menu item still bypasses the unsaved-changes guard entirely (see
`docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md` for the full root-cause record: it is wired
directly to AppKit's `terminate:`, bypassing `WindowEvent::CloseRequested`). This milestone builds
no native menu infrastructure (explicitly forbidden by §3) and does not touch this behavior.
Tracked in `docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md`'s checklist and reserved for
**Build 025 M4**.

## Scope discipline

No engine, protocol, sidecar, or Rust command change (`git diff --quiet` against
`desktop/src-tauri/src/` and `src/zerorod_sidecar/`/`src/zerorodcad/` is part of the validation
gate) — this milestone's entire surface is frontend-only:
`desktop/frontend/src/{main,parameter_panel,startup,diagnostics_panel}.ts` plus `style.css` and
tests. `project.py`, `project_panel.ts`, `project_state.ts`, `live_preview.ts`, `scene.ts`,
`preview.ts`, `export.ts`, `export_panel.ts`, and the WebView capability list are all unchanged
(each individually confirmed via `git diff --quiet` in the validation gate). No new dependency was
added to `Cargo.toml` or `package.json`. No Build 025 M3 work (Reset/Fit View, visibility toggles,
Instrument Report) or M4 work (native menus, shortcuts, About, Quit fix) was started.

## Tests

- `parameter_panel.test.ts`: a new "automatic initial preview" suite — exactly-once fetch+commit
  for canonical defaults, accepted/draft consistency after the automatic load, a defaults-stage
  failure reported distinctly from a preview-stage failure, and a Retry-by-calling-`load()`-again
  success path. All 39 pre-existing tests in this file still pass, adjusted only for the new
  automatic preview call `load()` now makes during their own setup (mock-ordering fixes, not
  behavior changes to what they test).
- `startup.test.ts` (new): pure-function tests for the message/detail formatters, plus
  controller tests for the anti-flicker delay, the no-banner success case, the Retry/Show-Details
  failure surface, Retry re-invoking `io.run()`, a second failure replacing (not appending to) the
  first, exactly-one `io.run()` call per `start()`, and `dispose()` safely clearing a pending timer.
- `diagnostics_panel.test.ts` (new): no fetch before the user opens it, a successful open showing
  all expected rows, a sanitized last-engine-error row, graceful partial-failure handling (sidecar
  status alone unreachable), a full error state (app_info/engine_status failing), collapse/re-open
  without re-fetching, Refresh Status re-fetching, and an explicit assertion that only "Hide
  Diagnostics"/"Refresh Status" buttons exist (no kill-sidecar/process-control action).
- Rust: no source changed, so no new Rust tests were needed; `cargo test` (including the Build 025
  M1 `native_close_permission` regression test) re-run unchanged and still passes.
- Full frontend suite: 291 passed, 1 skipped (0 new skips) after this milestone's additions.

## Gate

`scripts/validate-build025-m2.sh` re-verifies the still-valid subset of Build 025 M1's own checks
directly (documented `EXPECTED_AUTHORIZED_DRIFT` for the one check that legitimately changed —
`app_info()`'s rendering moved from `main.ts` to `diagnostics_panel.ts`, replaced with an equivalent
check against the new location) plus this milestone's own new checks, then rebuilds the productive
sidecar and a fresh release `.app` end to end. See the milestone's Abschlussbericht for the actual
recorded run result.
