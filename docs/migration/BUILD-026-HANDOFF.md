# Build 026 — Handoff: Production Packaging & macOS Integration

This document prepares Build 026; it does not start it. Nothing here authorizes implementation
work — it exists so Build 026 can begin from a written understanding of what it inherits, what it
owns, and what it explicitly should not touch. Build 025
(`docs/migration/BUILD-025-COMPLETION.md`) is **COMPLETE** — Desktop Feature Parity is established
within its approved scope: project persistence, a productized lifecycle UI, preview/report parity,
and a native macOS desktop shell (menus, shortcuts, About, a unified Quit/close guard) are all real,
tested, human-validated, and productive. Build 026's job, per the accepted `ROADMAP.md` build
sequence, is **Production Packaging & macOS Integration**.

## What Build 026 inherits from Build 022–025 (proven, stable, reusable)

- **The persistent engine** (`desktop/src-tauri/src/engine.rs`): lazy spawn, persistent reuse,
  30 s timeout, crash detection + restart-once, graceful shutdown. Unchanged since Build 024 M1.
- **The full command set**: preview, parameters, export (STL/STEP/report), report, project
  open/save, and view-menu-checkbox sync — 18 registered Tauri commands, each with its own
  `tauri::test::get_ipc_response` IPC-boundary regression test where the payload has an underscored
  key (`rename_all = "snake_case")`, per the pattern `docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md`
  established.
- **Project persistence**: New/Open/Save/Save As against the existing, unmodified `.zerorod`
  format (`src/zerorodcad/project.py`), with `project_dirty` derived from `accepted` vs. the
  last-saved baseline, and a Save/Discard/Cancel guard covering New, Open, and Quit/window-close.
- **The unified close/quit guard**: the red macOS close button and native ⌘Q both resolve through
  the exact same `confirmQuit()` decision (`project_panel.ts`) via the same native
  `WebviewWindow::close()` event pipeline — not two implementations. `close_flow.ts` makes
  overlapping close attempts resolve to exactly one guard decision. Any future close-adjacent
  feature (e.g. a "confirm before quit during export" enhancement) must extend this single guard,
  never add a second path.
- **The native desktop shell**: `desktop/src-tauri/src/menu.rs` (Application/File/View menu,
  ⌘N/⌘O/⌘S/⇧⌘S/⌘Q, native About), routed to the exact same controller methods the visible UI calls
  — no duplicated command/decision logic in Rust.
- **The accepted-state pattern**: `accepted` vs. `draft`, reused unmodified by export, report, and
  project save.
- **The two-layer output/result verification pattern**: sidecar-side existence/non-empty check plus
  independent Rust-side structural validation (`export_result.rs`) before any success value reaches
  the WebView.
- **The security boundary**: WebView capability is exactly `["core:default", "dialog:allow-open",
  "dialog:allow-save", "core:window:allow-destroy"]` — no filesystem/shell/process grant. Any new
  Build 026 native-OS interaction (installer flow, code-signing-adjacent UI, if any) must go through
  a Tauri-mediated, narrowly-scoped command or capability — never a raw WebView-side file API.
- **The packaging/validation infrastructure**: `scripts/build-productive-desktop-app.sh` (sidecar
  PyInstaller onedir → Tauri release build → hash-gated dylib dedup), and the per-milestone
  `validate-buildNNN*.sh` / `validate-buildNNN.sh` master-gate pattern — each milestone/build
  re-verifies the *current, integrated* state directly rather than chain-calling earlier scripts.
  `scripts/validate-build025.sh` is the current reference master gate.
- **A clean repository**: Build 025 M5's cleanup discovery pass found 0 dead code paths, 0 orphaned
  scripts, 0 tracked generated artifacts. Build 026 inherits a repository with no cleanup debt.

## What Build 026 owns (per `ROADMAP.md`'s Build 026 entry)

- Production bundle (the release packaging pipeline hardened for actual distribution, not just
  validation builds).
- Final dependency audit.
- Performance baseline (for the distributable artifact specifically).
- Signing preparation.
- Notarization preparation.
- Release workflow.

Per `ROADMAP.md`: *"Signing/notarization is planned only at the build-planning level here; no new
signing/notarization subproject is started by this roadmap entry."* Build 026's own mandate decides
how literally that is read.

## Explicit non-goals for Build 026 (per the accepted build sequence)

- PySide6 removal — that is the **Post-Build-026 — PySide6 Retirement Decision** roadmap entry, and
  is explicitly gated on: feature parity confirmed (Build 025 established this), real-world testing
  complete, a rollback package archived, and a final architecture review. None of those four gates
  are satisfied by Build 026 itself finishing.
- Settings, Recent Files, drag & drop, file associations/Finder integration — never scoped into any
  Build 022–025 milestone; still open product surface, not assumed into Build 026 by this document.
- Any redesign of the Three.js renderer, live-preview scheduling, the Rust process/lifecycle model,
  the parameter/export/report contracts, project persistence, or the native menu/shortcut/quit-guard
  architecture — Build 026 packages and ships what Builds 022–025 established, it does not redesign
  it.

## Known constraints to design within

- **The productive build path is `packaging/tauri/sidecar-onedir.spec` +
  `scripts/build-productive-desktop-app.sh`.** A separate, older script family
  (`scripts/build_macos_app.sh`, `package_macos_release.sh`, etc.) exists but targets the legacy
  PySide6 `.app` — it is not a competing productive Tauri pipeline and should not be adapted for
  signing/notarization without first confirming that's actually intended (see
  `docs/migration/BUILD-025-M5-REPOSITORY-CLEANUP.md` §6 for the full classification).
- **The current release bundle is unsigned.** First launch requires the standard Gatekeeper
  right-click → Open override — expected, not a defect, until Build 026 addresses it.
- **Artifact-identity discipline**: every Build 022–025 milestone that shipped a human-validation
  artifact used a uniquely-named `.app` copy (never overwriting the canonical `ZeroRodCAD.app`) plus
  explicit identity proof (frontend asset hash, a compiled marker string, a deterministic bundle
  fingerprint). Continue this discipline for any signed/notarized artifact Build 026 produces —
  signing changes the bundle's byte-for-byte reproducibility in ways that need to be understood and
  documented, not silently accepted.

## Suggested first steps (not prescriptive — Build 026's own mandate decides)

1. Read `docs/migration/BUILD-025-COMPLETION.md` and `BUILD-025-M5-REPOSITORY-CLEANUP.md` for the
   exact current architecture/dependency/security baseline before making any packaging change.
2. Decide, with evidence, what "production bundle" concretely changes vs. the existing
   `build-productive-desktop-app.sh release` output — don't assume a new pipeline is needed without
   a concretely demonstrated gap.
3. Treat signing/notarization preparation as literally that — preparation — unless Build 026's own
   mandate explicitly authorizes obtaining/using real Apple Developer credentials and submitting a
   real notarization request.

No implementation of the above is authorized by this document — it is a handoff, not a plan.
