# Build 024 — Handoff: STL / STEP Export Workflow

This document prepares Build 024; it does not start it. Nothing here authorizes implementation
work — it exists so Build 024 can begin from a written understanding of what it inherits, what it
owns, and what it explicitly should not touch. Build 023 (`docs/migration/BUILD-023-COMPLETION.md`)
is **COMPLETE** — parameter editing and live-preview regeneration are now real, tested, and
productive. Build 024's job is to make the resulting model exportable.

## What Build 024 inherits from Build 023 (proven, stable, reusable)

- **The persistent engine** (`desktop/src-tauri/src/engine.rs`): lazy spawn, persistent reuse,
  timeout, crash detection + restart-once, graceful shutdown. An export request is still just
  another request through the same `engine::request` entry point — no new process-lifecycle code
  should be needed.
- **The parameter state the user is actually looking at**: `parameter_panel.ts`'s `accepted` —
  "the parameter values currently represented in the preview, or the last state a completed round
  trip confirmed" (see `docs/migration/BUILD-023-M4-LIVE-PREVIEW.md`'s "State semantics"). This is
  the natural candidate for "what does Export STL/STEP actually export" — not the possibly-still-
  debouncing `draft`.
- **The Rust command boundary pattern** (`desktop/src-tauri/src/commands.rs`): new commands are
  added, never bolted onto existing ones with new optional parameters — `engine_preview_mesh` and
  `engine_preview_mesh_with_parameters` coexist rather than one growing a flag. An export command
  should follow the same pattern (e.g. `engine_export_stl`/`engine_export_step`, or a combined
  `engine_export`), not overload the preview commands.
- **The sidecar** (`src/zerorod_sidecar/`): already imports `zerorodcad.parameters`/
  `zerorodcad.validation`; a new `export` command handler would follow `_run_preview_command`'s
  exact pattern — parse the `zerorod-parameters/v1` request (reusing `parameters_contract.py`
  unmodified), validate with `zerorodcad.validation.validate_parameters` (Level 3), then call the
  engine-level export function below (Level 4-equivalent).
- **The existing engine-level STL/STEP export**, already fully built and unrelated to the desktop
  migration: `src/zerorodcad/export.py`'s `export_project(output_directory, parameters)` —
  validates parameters, lazily imports `cadquery.exporters` (kept lazy for the same reason the
  sidecar itself defers CadQuery imports — packaged-app startup latency), and writes
  `<project>-body.stl`, `<project>-assembly.step`, and `<project>-report.md` into a given directory.
  This function needs no rewrite; Build 024's job is exposing it through the Tauri boundary with a
  real save-location dialog, not reimplementing export logic.
- **The structured error model**: `EngineError`/`isEngineError`, `SidecarError`, the
  `{code, message, details?}` envelope shape — already generalizes to export-specific error codes
  (e.g. a write-permission failure, a disk-full condition) without protocol changes.
- **The security boundary**: WebView still gets no filesystem/shell/process permission directly.
  A native save dialog must go through Tauri's own dialog plugin/command (Rust-mediated), never a
  raw filesystem path typed into the WebView or a shell-out.

## What Build 024 owns

- **Export UI**: a trigger (likely near Apply, operating on `accepted`) and status/progress
  presentation for STL and STEP export.
- **Native save dialogs**: through the approved Tauri/Rust boundary (a dialog plugin or an
  app-registered command) — never a WebView-side file API.
- **The parameter-to-export request flow**: deciding whether export uses a dedicated Rust command
  (recommended, matching the "new command over overloaded existing one" pattern above) or reuses an
  existing one is a Build 024 design decision, not predetermined here.
- **Export status/error UX**: success confirmation, in-progress indication, and structured
  error presentation (reusing the `EngineError`/`isEngineError` pattern already established).
- **Overwrite behavior**: what happens when the chosen save location already contains a file with
  the same name — a genuine Build 024 product decision.
- **Regression comparison with the legacy PySide6 reference app**, which already has working
  STL/STEP export via the same `zerorodcad.export.export_project` — useful as a behavioral reference
  (what fields end up in the filename, what the report contains), not something to port mechanically
  or treat as UI-authoritative (the same caution Build 023 M1 applied to legacy parameter ranges).

## Known constraints to design within

- **Timeout**: the sidecar's request timeout is 30 s (`engine::REQUEST_TIMEOUT_SECS`, unchanged
  since Build 022). STL/STEP export (especially STEP assembly export) may take longer than a preview
  tessellation — measure before assuming the existing timeout is sufficient; if not, that becomes a
  Build 024 design question, not something to silently bump without evidence (the same discipline
  Build 023's own handoff applied to itself).
- **Serialized request queue**: `engine.rs`'s `Mutex`-guarded state serializes all requests. An
  export request will queue behind (or block) a live-preview request if one is in flight — worth
  designing the UI around explicitly (e.g. disable export while a live-preview request is pending)
  rather than fighting it.
- **No parameter validation currently crosses the export boundary** — today nothing exports at all
  from the Tauri app, so this is genuinely new surface, not a placeholder to remove (unlike Build
  023 M1's `unsupported_parameters` situation).
- **File system access must stay narrow**: only the user-chosen save location, only via the native
  dialog's own return value — no directory listing, no arbitrary path read/write capability granted
  to the WebView.

## Explicit non-goals for Build 024 (per the accepted build sequence)

- Project persistence / open-save workflow (Build 025).
- Full desktop feature parity — settings, shortcuts, accessibility (Build 025).
- Production packaging, signing, notarization (Build 026).
- PySide6 removal (Post-Build-026 decision).
- Any change to the Three.js renderer, live-preview scheduling, the Rust process/lifecycle model, the
  parameter contract, or the packaging baseline — Build 024 is additive to what Build 023
  established, not a redesign of it.

## Suggested first steps (not prescriptive — Build 024's own mandate decides)

1. Read `src/zerorodcad/export.py` and the legacy PySide6 export UI
   (`src/zerorodcad_desktop/`, reference only) to understand current export behavior and naming
   conventions before designing the Tauri-side flow.
2. Decide the export command shape: reuse `accepted` parameters implicitly, or accept an explicit
   parameter set like `engine_preview_mesh_with_parameters` does — likely the former, since export
   naturally targets "what's currently shown," not an arbitrary draft.
3. Design the native save-dialog integration first (which Tauri plugin/capability, what
   permission grant it needs) before writing UI code — this is the one place Build 024 genuinely
   expands the security boundary, so it deserves explicit design attention up front.
4. Measure STL/STEP export latency against the existing 30 s timeout before assuming it's adequate.

No implementation of the above is authorized by this document — it is a handoff, not a plan.
