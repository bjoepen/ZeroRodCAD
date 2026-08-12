# Build 025 — Lifecycle Analysis

Discovery document, produced before any Build 025 implementation. Analyzes the current Build-024
lifecycle, the technical controls currently visible in the product UI, and derives a target
lifecycle consistent with the mandate's binding principle:

> **ZeroRodCAD besitzt eine Engine. Der Benutzer startet keine Engine.**

## 1. Current Build-024 lifecycle (as implemented)

```text
App Launch (Tauri/Rust process starts, WebView loads)
    ↓
main.ts init() runs:
    - renders empty status panel (all rows NOT_READY/STOPPED)
    - fetchAppInfo() → "rust-bridge" row READY
    - fetchEngineStatus() → Rust-local status only, does NOT spawn the sidecar
      (engine.rs's status() uses try_lock, never calls ensure_started)
    - parameterPanel.load() → fetches `parameters_defaults`, which DOES call
      engine::request() → ensure_started() → lazily spawns the sidecar on
      this first real IPC round trip
    ↓
Parameter panel renders with defaults; live-preview scheduler is armed
    ↓
Viewport stays EMPTY — no preview mesh has been requested yet
    ↓
User must manually click "Load / Refresh ZeroRod" (or edit a parameter,
triggering the debounced live-preview path) to see a model at all
```

Evidence: `main.ts:186-208` (`init()`), `parameter_panel.ts:494-502` (`load()` fetches defaults
only, never calls `preview.load()`/`fetchPreview`), `engine.rs:263-290` (`status()` is
non-blocking and does not spawn), `engine.rs:194-248` (`ensure_started`/`request` — the actual lazy
spawn point, reached via `parameters_defaults` → `engine_parameters_defaults` → `engine::request`).

**Sidecar spawn trigger, precisely:** the *first* call to `engine::request()` from *any* command
— in practice this is `engine_parameters_defaults`, called automatically by
`parameterPanel.load()` during `init()`. So the sidecar is already started automatically, lazily,
within roughly one IPC round trip of app launch — the mandate's "no manual engine start" principle
is **already substantially met at the process level**. What is *not* met is the **preview** level:
nothing automatically requests or renders a mesh, so the user's very first impression of the app is
an empty viewport next to four technical buttons, one of which they must click to see the actual
product.

## 2. Visible technical controls (current product UI)

| Control | Location | Rust command invoked | What it actually does |
|---|---|---|---|
| Status panel: 5 rows (`Desktop shell`, `Rust bridge`, `Python sidecar`, `CAD engine`, `3D preview`) with raw enum values (`READY`/`NOT_READY`/`STOPPED`/`RUNNING`/`CONNECTED`/`ERROR`) | `main.ts:22-44,52-58,64-74` | `app_info`, `engine_status` | Surfaces internal process/IPC/render lifecycle state directly in the main window, at all times |
| "Start / Check Engine" button | `main.ts:30,86-98,167-169` | `engine_ping` (via `pingEngine()`), then `engine_status` | Manually pings the sidecar and reports pid/latency — a debug affordance, not a product action |
| "Ping Engine" button | `main.ts:31,100-115,170-172` | `engine_sidecar_status` (via `fetchSidecarStatus()`) | Dumps raw sidecar diagnostics (Python/CadQuery/OCP/VTK versions) into the "last action" text as JSON |
| "Request Preview Data" button | `main.ts:32,117-131,173-175` | `engine_preview` | Explicitly documented in its own success text as **not rendering anything** — a mesh-summary diagnostic only |
| "Load / Refresh ZeroRod" button | `main.ts:33,176-178` | `engine_preview_mesh` (via `preview.load()`) | The **only** trigger that actually renders the model — this one has genuine product value (see §1) |
| "last-action" `<pre>` block | `main.ts:35,47,76-78` | — | Free-text log of the most recent technical action, including raw error codes |

All five controls sit in the main window's `sidebar`/`actions` section, alongside — not behind a
separate area from — the parameter panel and export panel, which are the actual product surfaces
(`main.ts:26-43`).

## 3. Classification (mandate §10)

| Control | Classification | Rationale |
|---|---|---|
| Status panel (5 rows) | `MOVE_TO_DIAGNOSTICS` | Genuinely useful for support/debugging (mirrors legacy's `DiagnosticsDialog`, see Desktop Integration Analysis), but does not belong in the primary product surface — a user opening ZeroRodCAD to design an instrument has no reason to see "Rust bridge: READY" |
| "Start / Check Engine" | `REMOVE_FROM_PRODUCT_UI` | Redundant once the sidecar auto-starts and the viewport auto-loads (§1) — nothing left for the user to manually "start" or "check" in normal use; its diagnostic value (pid, ping latency) can live in Diagnostics if kept at all |
| "Ping Engine" | `MOVE_TO_DIAGNOSTICS` | Its version/variant output is exactly the content of legacy's Diagnostics dialog (`diagnostics.py`'s CadQuery/PySide6/Python version rows) — relocate, don't delete |
| "Request Preview Data" | `REMOVE_FROM_PRODUCT_UI` | Self-documented as a non-rendering diagnostic; superseded by an automatic initial preview load (§1) plus, if still wanted, a mesh-summary row in Diagnostics |
| "Load / Refresh ZeroRod" | `REDESIGN_FOR_TAURI` (not remove) | Its *capability* (fetch + render the current model) is genuinely needed — but it should fire automatically at startup (closing the Feature Parity Matrix's "no automatic initial preview" gap) rather than requiring a manual click styled identically to the three debug buttons above it. A manual "Reset/Refresh View" affordance can remain as a legitimate product control once redesigned outside the technical-actions block. |
| "last-action" log | `MOVE_TO_DIAGNOSTICS` | Useful for support, not for normal product use; raw error codes/JSON have no place in the primary UI per the mandate's Error UX goal (§26/§27) |

## 4. Target lifecycle

```text
App Launch
    ↓
Tauri/Rust initialization (WebView loads, IPC bridge ready)
    ↓
UI appears immediately (parameter panel + viewport skeleton), no blocking wait
    ↓
Engine state is determined internally:
    - parameters_defaults round trip lazily spawns the sidecar (unchanged
      from today — engine.rs's existing lazy-start behavior is already
      correct and needs no redesign)
    ↓
An initial preview mesh is requested and rendered automatically
    (closes the "empty viewport on first launch" gap identified in §1 —
    this is the one concrete lifecycle behavior change Build 025 should make)
    ↓
Ready — user edits parameters, live preview updates, exports, etc.

(If the sidecar fails to spawn or the first request times out/crashes:)
    ↓
A friendly failure surface appears (see §5) instead of a raw error code
in a technical log the user was never looking at
```

This target is a **small, additive change** to the existing lifecycle, not a redesign: `engine.rs`'s
lazy-spawn/timeout/crash-restart/shutdown machinery is unchanged (mandate §49 forbids redesigning
it without an ADR, and no evidence here suggests a need to). The only functional change is
"request+render an initial preview automatically instead of waiting for a manual click," plus
relocating the four technical controls out of the primary UI.

## 5. Startup failure UX

Currently, a sidecar spawn failure or first-request timeout surfaces only as an `ERROR` value in
the (currently product-visible, soon-to-be-Diagnostics-only) status panel, or a raw
`EngineError.code`/`message` string in "last action" text (`main.ts:92-97`). There is no dedicated
failure surface comparable to legacy's `QMessageBox.critical(None, "{APP_NAME} could not start",
"{exc}\n\nDiagnostic log:\n{log_path}")` (`app.py:78-91`).

Recommendation (design only, not implementation — mandate §27): a plain-language message ("ZeroRodCAD's
engine could not start.") with **Retry** (re-attempt the lazy spawn), **Show Details** (reveals the
structured `EngineError` — code, message, and `details` if present — for support purposes, without
ever showing a raw Python traceback, consistent with the existing `zerorod-sidecar/v1` "never a raw
traceback crosses the boundary" invariant), and **Quit**. This is new frontend-only UX; it requires
no protocol or engine-layer change since `EngineError` already carries everything needed
(`protocol.rs:14-24`).

## 6. Automatic recovery

Already implemented and already transparent to the user: `engine.rs:214-248`'s `request()` detects
`sidecar_crashed`/`timeout`, kills the dead process, restarts once, and retries the same request
without the caller (or the user) doing anything — this already satisfies the mandate §28 goal ("kein
manueller Restart-Zwang"). The only remaining question is what happens when the *retry itself* also
fails — today that surfaces as a normal `EngineError` through whatever command triggered it, which
after the relocation in §3 would appropriately land in the new startup/runtime failure surface (§5)
rather than a diagnostics-only log the user isn't looking at during active work.

## 7. App shutdown

Already matches the mandate's target shape:

```text
User quits (⌘Q or window close)
    ↓
Tauri's ExitRequested event fires
    ↓
engine::kill_if_running() force-kills any live sidecar (non-blocking,
best-effort — lib.rs:52-53)
    ↓
App exits
```

Evidence: `lib.rs:45-55`, `engine.rs:292-306`. Zero orphan-process risk was already verified in
Build 022 (persistent+onedir was chosen specifically because forced-kill leaves no orphan, unlike
the rejected onefile alternative — `ADR-022-001` "Considered alternatives"). The one gap is
upstream of shutdown, not shutdown itself: today there is no unsaved-changes check before quitting,
because there is nothing yet to have unsaved changes *in* (no project persistence exists). Once
Project Persistence is built, the quit path needs an "unsaved project?" check inserted before the
`ExitRequested` handler's kill — see Project Persistence Analysis §"Close/Quit with unsaved
changes."

## 8. Engine-state model (analysis only, per mandate §9 — not authorized for implementation)

The existing Rust-side `LifecycleState` enum (`engine.rs:47-53`: `Stopped`/`Running`/`Error`) is
coarser than the mandate's suggested `initializing`/`ready`/`busy`/`recovering`/`error`/
`shutting_down` model. Whether a finer-grained state machine is actually needed depends entirely on
what the relocated Diagnostics area and the new startup-failure UX (§5) need to distinguish — e.g.
"busy" (a request in flight) is already implicitly derivable from `EngineState`'s mutex being held
(`engine.rs:264,284-289` already treats a held lock as "Running"), so a new explicit state may be
redundant. **Recommendation: do not introduce a new state enum speculatively.** If the Diagnostics
area or failure UX design (both DECISION_REQUIRED / not yet scoped) concretely need a distinction
`LifecycleState` can't express, add it then, evidenced by that need — not now.

## 9. Risks

- Making the initial preview load automatic adds one more IPC round trip to perceived startup time
  (~0.12 s warm, ~1.45 s cold per Build 024's measured export timing, which uses the same request
  path) — negligible against the existing ~0.6 s sidecar cold-start baseline, but should be
  re-measured once implemented, not assumed.
- Relocating the technical controls must not silently remove the *capability* they provide (pid,
  ping latency, sidecar version info) — Diagnostics needs to actually carry it forward, not just
  delete the buttons.
- No engine-layer, protocol, or architecture change is implied by anything in this analysis — the
  entire lifecycle change surface is frontend-only (`main.ts`, plus wherever Diagnostics ends up
  living).

## 10. Tests needed

- Automated: an initial-load test proving the viewport receives and renders a mesh without any user
  interaction after `init()` completes (extends the existing `preview.test.ts`/`scene.test.ts`
  coverage).
- Automated: a startup-failure-path test simulating a spawn failure and asserting the new failure
  surface (once designed) receives the structured `EngineError`, not a raw string.
- Human validation: required — this changes what the user sees in the first seconds after launch,
  which Build 022–024's own precedent treats as always needing a real human pass (`ADR-022-001`
  "Known risks": "Interactive WebView confirmation has ... only ever been closed by a human tester").
