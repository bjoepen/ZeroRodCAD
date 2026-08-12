# Build 025 — Handoff: Desktop Feature Parity

This document prepares Build 025; it does not start it. Nothing here authorizes implementation
work — it exists so Build 025 can begin from a written understanding of what it inherits, what it
owns, and what it explicitly should not touch. Build 024
(`docs/migration/BUILD-024-COMPLETION.md`) is **COMPLETE** — parameter editing, live preview, and a
robust, human-validated STL/STEP/report export workflow are now real, tested, and productive.
Build 025's job, per the accepted `ROADMAP.md` build sequence, is **Desktop Feature Parity**.

## What Build 025 inherits from Build 022–024 (proven, stable, reusable)

- **The persistent engine** (`desktop/src-tauri/src/engine.rs`): lazy spawn, persistent reuse,
  30 s timeout, crash detection + restart-once, graceful shutdown. Byte-for-byte unchanged since
  Build 024 M1. Any new Build 025 request is still just another request through the same
  `engine::request` entry point.
- **The parameter model & contract** (`zerorod-parameters/v1`): the canonical request shape,
  defaults, and validation, sourced unmodified from `zerorodcad.parameters`/`zerorodcad.validation`.
- **The accepted-state pattern**: `accepted` (the parameter values currently represented in the
  preview, or the last state a completed round trip confirmed) vs. `draft` (possibly still
  debouncing) — established in Build 023 M4, reused unmodified by Build 024's export workflow. Any
  new Build 025 feature that needs "the model the user is currently looking at" should reuse this
  distinction rather than inventing a third state.
- **The Rust command boundary pattern** (`desktop/src-tauri/src/commands.rs`): new commands are
  added, never bolted onto existing ones with new optional parameters. Any command with an
  underscored parameter name needs `#[tauri::command(rename_all = "snake_case")]` — see
  `docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md` for the real defect this guards against, and test
  it with a real `tauri::test::get_ipc_response` dispatch, not a mocked `invoke()` assertion.
  `desktop/src-tauri/src/commands.rs`'s `ipc_argument_binding` module is the reference pattern.
- **The two-layer output/result verification pattern**: a sidecar-side existence/non-empty check
  plus an independent Rust-side structural validation (`export_result.rs`) before any success value
  reaches the WebView. Any new Build 025 feature that writes to disk or returns a structured payload
  should consider the same two-layer discipline rather than trusting a single boundary.
- **The native dialog boundary**: `tauri-plugin-dialog`, narrowly scoped per capability
  (`dialog:allow-open` only so far). A save-dialog or project-open/save workflow will need its own
  narrow, explicitly justified capability addition — never a broad filesystem grant.
- **The structured error model**: `EngineError`/`isEngineError`, `SidecarError`, the
  `{code, message, details?}` envelope — already generalizes to new error codes without protocol
  changes.
- **The security boundary**: WebView still gets no filesystem/shell/process permission directly.
  Every new native-OS interaction (file dialogs, shortcuts, desktop integration) must go through a
  Tauri-mediated, narrowly-scoped command — never a raw WebView-side file API or shell-out.
- **The packaging/validation infrastructure**: `scripts/build-productive-desktop-app.sh`,
  hash-gated dylib dedup, and the per-milestone `validate-buildNNN*.sh` gate pattern (each milestone
  re-verifies frozen invariants directly rather than chain-calling earlier scripts, since later
  milestones legitimately touch the same files — see `scripts/validate-build024.sh`'s header for the
  rationale).

## What Build 025 owns (per `ROADMAP.md`'s Build 025 entry)

- Remaining application workflows (whatever the legacy PySide6 reference app already does that the
  Tauri app does not yet).
- Settings.
- Project open/save (persistence) — genuinely new surface; nothing in Build 022–024 implements or
  assumes this.
- Shortcuts.
- Desktop integration.
- Accessibility.
- Parity validation against the legacy PySide6 reference (the same "reference, not UI-authoritative"
  caution Build 023 M1 applied to legacy parameter ranges, and Build 024's handoff applied to legacy
  export field-naming, continues to apply).

This scope is exactly `ROADMAP.md`'s existing Build 025 entry — no new scope is invented here.

## Known constraints to design within

- **Serialized request queue**: `engine.rs`'s `Mutex`-guarded state serializes all requests. Any
  new Build 025 request type will queue behind (or block) a live-preview or export request if one
  is in flight — the same design consideration Build 024's own handoff flagged for export.
- **Project persistence has no existing contract.** Unlike export (which reused
  `zerorodcad.export.export_project` unmodified), project open/save has no equivalent
  already-built engine-level function to expose — this is genuinely new design work, not a
  boundary-exposure exercise like Build 024 largely was.
- **The WebView security boundary does not move.** Every new capability addition needs the same
  explicit, narrow, documented justification `dialog:allow-open` received in Build 024 M1.

## Explicit non-goals for Build 025 (per the accepted build sequence)

- Production packaging, signing, notarization (Build 026).
- PySide6 removal (Post-Build-026 decision).
- Any redesign of the Three.js renderer, live-preview scheduling, the Rust process/lifecycle model,
  the parameter contract, the export workflow, or the packaging baseline — Build 025 is additive to
  what Builds 022–024 established, not a redesign of it.

## Suggested first steps (not prescriptive — Build 025's own mandate decides)

1. Read the legacy PySide6 desktop app (`src/zerorodcad_desktop/`, reference only) to inventory
   which workflows/settings/shortcuts it has that the Tauri app doesn't yet — the same
   "reference, not authoritative" discipline used throughout this migration.
2. Design the project-persistence data shape and its own request/response contract before writing
   UI code, the same way Build 024 designed its native-dialog integration before UI work — this is
   the one place Build 025 genuinely expands both the security boundary (a save dialog) and the
   sidecar/engine surface (no existing `export_project`-equivalent function to reuse).
3. Decide, with evidence, whether project persistence needs a new sidecar command/contract version
   or fits within `zerorod-sidecar/v1`'s existing envelope — don't assume a protocol bump is needed
   without a concretely demonstrated need, per this migration's own "contracts are stable by
   default" principle.

No implementation of the above is authorized by this document — it is a handoff, not a plan.
