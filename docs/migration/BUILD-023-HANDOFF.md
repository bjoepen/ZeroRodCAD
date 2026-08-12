# Build 023 — Handoff: Parameters & Live Preview

This document prepares Build 023; it does not start it. Nothing here authorizes implementation
work — it exists so Build 023 can begin from a written understanding of what it inherits, what it
owns, and what it explicitly should not touch.

## Purpose

Build 023's goal, per `ROADMAP.md`: a full `ZeroRodParameters` UI, validation, live regeneration,
responsive preview, and error presentation. Where Build 022 proved the pipeline works for the
*default* ZeroRod (the only parameter set every milestone's `preview` command has ever requested),
Build 023 makes that pipeline parameter-driven.

## What Build 023 inherits from Build 022 (proven, stable, reusable)

- **The full render pipeline** (`desktop/frontend/src/{mesh,scene,preview}.ts`): validated
  `zerorod-mesh/v1` → `BufferGeometry` conversion, camera fit, `OrbitControls`, resize, refresh
  without stale geometry, disposal. Build 023 should not need to touch this — a parameter-driven
  preview still ends at the same mesh contract.
- **The Rust engine manager** (`desktop/src-tauri/src/engine.rs`): lazy spawn, persistent reuse,
  timeout, crash detection + restart-once, graceful shutdown. Parameter-driven requests are still
  just `preview` requests with a non-empty `parameters` object — the lifecycle code needs no
  changes to handle them.
- **The productive sidecar** (`src/zerorod_sidecar/`): already imports
  `zerorodcad.parameters`/`zerorodcad.preview` — the underlying `zerorodcad.parameters.ZeroRodParameters`
  dataclass and `build_preview_scene()` function are untouched by the whole desktop migration and
  already support arbitrary parameter values at the library level.
- **The packaging baseline** (`packaging/tauri/sidecar-onedir.spec`,
  `packaging/tauri/dedup_bundle_dylibs.py`, `scripts/build-productive-desktop-app.sh`): unaffected
  by a parameter UI; reuse as-is.

## What Build 023 owns

- **Parameter UI**: a form/editor surface for `ZeroRodParameters`' fields in the WebView.
- **Validation**: client-side and/or server-side rejection of invalid parameter combinations
  before a request is sent — `zerorodcad.validation` already exists at the library level
  (`ValidationResult`, `validate_parameters`) and is a natural reuse candidate, not something to
  reinvent.
- **The parameter-to-engine request flow**: today, `src/zerorod_sidecar/main.py`'s `preview`
  command hard-rejects any non-empty `parameters` object
  (`SidecarError("unsupported_parameters", ...)`, `desktop/src-tauri/src/commands.rs`'s
  `engine_preview_mesh` passes whatever it's given straight through). Build 023 needs to actually
  accept and use a non-empty parameters object — this is a **real, necessary protocol-surface
  change**, not a violation of "no protocol reinvention": the `zerorod-sidecar/v1` envelope shape
  (`schema`/`request_id`/`command`/`parameters`) already supports this; only the `preview` command
  handler's behavior needs to change from "reject non-default" to "use what's given."
- **Regenerated mesh / live update behavior**: deciding the UX for "parameter changed → preview
  regenerates" (debounced live updates vs. an explicit "Apply" action) is a Build 023 product
  decision, not predetermined here.

## Known constraints to design within

- **Timeout**: the sidecar's request timeout is 30 s (`engine::REQUEST_TIMEOUT_SECS`). A
  parameter change that triggers a expensive re-tessellation still has to fit inside this, or the
  timeout value itself becomes a Build 023 design question — not something to silently bump
  without evidence.
- **Serialized request queue**: `engine.rs`'s `Mutex`-guarded state serializes all requests. Rapid
  parameter changes (e.g. a slider being dragged) will queue, not run concurrently — worth
  designing the UI around (e.g. debounce) rather than fighting.
- **No parameter validation currently crosses the IPC boundary**: today's `unsupported_parameters`
  rejection is the *only* parameter-related error path that exists productively. Build 023 needs a
  real validation-error UX, not just this placeholder.
- **PySide6 reference behavior**: `src/zerorodcad_desktop/` already has a working parameter-editing
  UI (Qt-based) that can inform Build 023's UX decisions — it is a feature-parity reference, not
  something to port mechanically.

## Explicit non-goals for Build 023 (per the accepted build sequence)

- STL/STEP export UI (Build 024).
- Full desktop feature parity — settings, project open/save, shortcuts (Build 025).
- Production packaging, signing, notarization (Build 026).
- PySide6 removal (Post-Build-026 decision).
- Any change to the Three.js renderer itself, the Rust process/lifecycle model, or the packaging
  baseline — Build 023 is additive to what Build 022 established, not a redesign of it.

## Suggested first steps (not prescriptive — Build 023's own mandate decides)

1. Extend `src/zerorod_sidecar/main.py`'s `_run_preview_command` to accept and use a non-empty
   `parameters` object (constructing a `ZeroRodParameters` from it, reusing
   `zerorodcad.validation.validate_parameters` for the rejection path).
2. Decide the validation-error contract: what `SidecarError` code(s) represent an invalid
   parameter set, and what the Rust/frontend error-handling path looks like (the existing
   `EngineError`/`isEngineError` pattern already generalizes to this).
3. Design the parameter UI's data flow before writing UI code — likely a typed parameter state
   object in the frontend, serialized into the `preview` request's `parameters` field.

No implementation of the above is authorized by this document — it is a handoff, not a plan.
