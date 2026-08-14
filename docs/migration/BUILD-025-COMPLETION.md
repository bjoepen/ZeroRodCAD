# Build 025 — Desktop Feature Parity — Completion Record

## Status

**COMPLETE.** All five milestones (M1–M5) are engineering-complete with Gate PASS; all four
product-facing milestones (M1–M4) are Human-Validation PASS. Master gate: `scripts/validate-build025.sh`
→ `BUILD-025 CONSISTENCY GATE: PASS`.

## Purpose

Build 022 proved the Tauri v2 + Rust + persistent Python sidecar + Three.js desktop architecture.
Build 023 made the model interactive. Build 024 made it exportable. Build 025 makes the application
a complete desktop product within its approved scope: real project files (New/Open/Save/Save As),
a productized lifecycle (automatic initial preview, no exposed engine-choreography controls), full
model-inspection parity with the legacy PySide6 reference (Reset View, layer visibility, an in-app
Instrument Report), and a native macOS desktop shell (Application/File/View menu, keyboard
shortcuts, About) — including the fix for the one carried-forward defect (native ⌘Q bypassing the
unsaved-changes guard). M5 (this record) is an integration and completion milestone: no new
product feature, a controlled repository cleanup pass, and closure of the build.

## Baseline

- Build 022/023/024: COMPLETE / PASS (own completion records).
- Build 025 M1 (`623d96b`, native-close bugfix `d3c93b9`): COMPLETE / Gate PASS, Human Validation PASS.
- Build 025 M2 (`781466d`): COMPLETE / Gate PASS, Human Validation PASS.
- Build 025 M3 (`9c8d1a3`): COMPLETE / Gate PASS, Human Validation PASS.
- Build 025 M4 (`195abb5`): COMPLETE / Gate PASS, Human Validation PASS.
- Build 025 M5 (this milestone): branched from `195abb5` as
  `feature/build025-m5-integration-completion`, working tree clean at branch time.

## Milestone Matrix

| Milestone | Engineering | Human Validation | Gate |
|---|---|---|---|
| M1 — Project Persistence | PASS | PASS | COMPLETE — `BUILD-025-M1: PASS` |
| M2 — Product UI Productization & Lifecycle Polish | PASS | PASS | COMPLETE — `BUILD-025-M2: PASS` |
| M3 — Preview & Report Parity | PASS | PASS | COMPLETE — `BUILD-025-M3: PASS` |
| M4 — Desktop Shell & Native Integration | PASS | PASS | COMPLETE — `BUILD-025-M4: PASS` |
| M5 — Integration, Completion & Repository Cleanup | PASS (master gate) | N/A — no runtime/product change made | COMPLETE — `BUILD-025: PASS` |

Per the mandate's own instruction, M5 does not require a redundant human click-through beyond what
M1–M4 already validated: it changed no runtime/product behavior (one build-identity constant and one
dead protocol field aside — see "Repository Cleanup") — only documentation, a master validation gate,
and a clean reproducible build.

## Human Validation Matrix

| Milestone | Result | Notes |
|---|---|---|
| M1 | **PASS** | Initial round found the red-close-button defect (`BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md` — a missing `core:window:allow-destroy` capability grant, not an application-logic defect). Fixed and re-validated PASS on 2026-08-13, authorizing M2 the same day. This milestone's own checklist document was not synchronized to that result at the time; corrected during M5 documentation cleanup — see `BUILD-025-M5-REPOSITORY-CLEANUP.md`. |
| M2 | **PASS** | Automatic initial preview, Diagnostics view, startup failure surface all confirmed working (`BUILD-025-M2-HUMAN-VALIDATION.md`). |
| M3 | **PASS** | Reset View, Body/Rod/Strings visibility, and the in-app Instrument Report confirmed working (`BUILD-025-M3-HUMAN-VALIDATION.md`). |
| M4 | **PASS** | Native menu, shortcuts, About, and — critically — the full ⌘Q/red-close dirty-state matrix confirmed working, closing the M1-tracked Quit-bypass gap (`BUILD-025-M4-HUMAN-VALIDATION.md`). Tester: Project Owner, 2026-08-13; overall result reported, individual checklist lines not itemized back into the document. |
| M5 | N/A | No product/runtime change made this milestone; nothing new for a human to validate. |

## Final Product Capabilities

```text
Launch                          -> automatic model on first paint (no manual "Load" click)
Parameter editing               -> all 16 zerorod-parameters/v1 fields, local validation, Reset
Live preview                    -> debounced (300 ms), stale-response-safe, camera-preserving
New / Open / Save / Save As     -> against the existing, unmodified .zerorod format
Dirty-state protection          -> Save/Discard/Cancel guard on New, Open, Quit/window-close
Reset View                      -> single control, camera refit from visible layers only
Body / Rod / Strings visibility -> presentation-only, survives live-preview geometry refresh
Instrument Report               -> in-app, sourced from accepted state, byte-identical to export
Export Model...                 -> native directory dialog, preflight, overwrite confirm, STL+STEP+report
Native menus                    -> Application / File / View (no Tauri default menu)
Native shortcuts                -> Cmd+N/O/S/Shift+Cmd+S/Cmd+Q, no dead zones, no double-trigger
About                           -> native dialog, sourced from the same app_info() Diagnostics uses
Diagnostics                     -> read-only engine/sidecar/build status, no side effects
Safe red close                  -> Save/Discard/Cancel guard, same pipeline as Cmd+Q
Safe Cmd+Q                      -> resumes through the identical confirmQuit() guard, re-entrancy-safe
Clean shutdown                  -> 0 orphan zerorod-engine processes after quit
```

No normal product control starts, pings, or shuts down the engine manually — Diagnostics is
read-only status, not a control surface. `ZeroRodCAD besitzt eine Engine. Der Benutzer startet keine
Engine.` — unchanged since Build 022, re-verified this milestone.

## Architecture

Unchanged from `ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md` (re-verified, 0 deviations):

```text
ZeroRodCAD Desktop 2.0
    Tauri v2 (native shell + WebView + Three.js preview)
    Rust process / IPC layer (owns the sidecar lifecycle end to end)
    Persistent Python 3.13 sidecar (PyInstaller onedir)
        ZeroRodCAD engine (unchanged) + CadQuery + cadquery-ocp-novtk
        Preview / Report / Export / Project I/O
```

- **Tauri**: v2, `@tauri-apps/cli`/`@tauri-apps/api` `^2.` pinned. Unchanged.
- **Three.js**: preview renderer, unchanged since Build 022 M3.
- **Rust process ownership**: `engine.rs` (lazy spawn, persistent reuse, 30 s timeout, crash
  detection + restart-once, graceful shutdown) is byte-for-byte unchanged since Build 024 M1 — every
  Build 025 feature (project I/O, report, menu routing) is "just another request" through the
  existing `engine::request` entry point.
- **Persistent sidecar**: `project_open`/`project_save`/`report` follow the same command-dispatch
  shape as `preview`/`export`; no second protocol, no second parser.
- **Python / CadQuery / cadquery-ocp-novtk**: unchanged; `zerorodcad.project`/`zerorodcad.report`
  remain canonical and were exposed, not reimplemented.
- **OCP strategy**: `cadquery-ocp-novtk` (not `cadquery-ocp`) confirmed in the packaging build
  environment and in the fresh M5 rebuild (0 VTK/PySide6/Qt/numba/llvmlite/scipy files found).
- **Packaging**: PyInstaller onedir, no onefile fallback, hash-gated dylib dedup.
- **IPC**: private `zerorod-sidecar/v1` JSON over stdin/stdout — no HTTP/WebSocket/gRPC.
- **WebView capability**: exactly `["core:default", "dialog:allow-open", "dialog:allow-save",
  "core:window:allow-destroy"]` — the four narrow, individually justified deltas introduced across
  Build 024 M1 and Build 025 M1. No `fs:*`, no `shell:*`/`process:*`, no `dialog:allow-message/ask/confirm`.
- **Native menu**: `desktop/src-tauri/src/menu.rs`, routed to the exact controller methods the
  visible UI already calls (`project_panel.ts`/`export_panel.ts`/`preview.ts`/`report_panel.ts`/
  `diagnostics_panel.ts`) — no duplicated command or decision logic in Rust.

**Deviations found: 0.**

## Project Persistence

New/Open/Save/Save As against the existing, unmodified `.zerorod` format (`src/zerorodcad/project.py`
— no new format invented). `project_dirty` is derived from `accepted` vs. the last-saved baseline
(never the still-debouncing draft), kept explicitly separate from the uncommitted-draft check. A
Save/Discard/Cancel guard covers New, Open, and Quit/window-close alike. Open is atomic — a failed
open leaves the current project completely untouched; the sidecar re-validates domain rules
(Level 3 defense-in-depth) rather than trusting a `.zerorod` file that may not have come from this
app's own Save. Re-proven this milestone via a real roundtrip through the freshly rebuilt sidecar
binary: `body_width: 38 -> 60`, save, open, verify the round-tripped value is exactly `60.0`.

## Lifecycle

Automatic initial preview on launch (`parameter_panel.ts`'s `load()`), a startup coordinator with an
anti-flicker "Preparing…" indicator and Retry/Show-Details on failure, and a Diagnostics view holding
all technical engine/sidecar status — no Start/Ping/Shutdown-Engine control anywhere in the product
UI. The persistent sidecar is lazily spawned by Rust on first request and reused for every subsequent
preview/export/report/project request; no per-request restart.

## Preview

Automatic on launch, debounced (300 ms) live regeneration on parameter change, generation-based
stale-response protection, in-flight request coalescing, and a camera-preservation heuristic so
small edits don't fight the user's manual framing. Reset View (`boundsFromVisibleObjects` feeding the
existing `fitCameraToBounds`) and Body/Rod/Strings visibility are both presentation-only — neither
calls the backend or dirties the project — and visibility survives a live-preview geometry refresh
(re-applied by `commitPreview` after every mesh replacement).

## Report

The in-app Instrument Report is sourced from `accepted` state only, via the sidecar `report` command
and Rust `engine_report` command, both reusing `zerorodcad.report.build_report` unmodified — the same
function `export`'s `report.md` uses. Re-proven byte-for-byte identical this milestone: the master
gate's live `report` command output for `body_width=60` contains the same `60.00 mm` figure as the
corresponding export's `report.md`.

## Export

Unchanged from Build 024 M1–M3: native directory dialog, preflight-then-confirm overwrite handling,
two-layer output verification (sidecar existence/non-empty check + Rust structural validation), and
accepted-state-only sourcing. Re-proven this milestone via the freshly rebuilt sidecar: default and
alternate-parameter exports both produce valid, non-empty STL/STEP/report files with correct,
attributable content; an invalid-parameter export request is rejected with a structured error and
does not disturb a subsequent valid request.

## Desktop Shell

An explicit native macOS Application/File/View menu (`menu.rs`) replaces Tauri's implicit default,
with native ⌘N/⌘O/⌘S/⇧⌘S/⌘Q accelerators. File/View items route to the exact same controller methods
the visible UI already calls — no duplicated command or decision logic in Rust. Show Body/Rod/Strings
have bidirectional native-menu-checkmark ↔ visible-checkbox sync through one shared funnel function
and a narrow, non-ACL-gated `set_view_menu_checked` command.

## Quit Architecture

The one defect carried across Build 025 M1–M3 is fixed in M4 and re-verified in M5: native "Quit
ZeroRodCAD" is a plain custom `MenuItem` (never `PredefinedMenuItem::quit`) whose handler calls
`WebviewWindow::close()` — the identical native event pipeline the already-validated red close button
uses — so ⌘Q now resumes through the single existing `confirmQuit()` guard, not a second
implementation. `close_flow.ts` makes overlapping close attempts (repeated ⌘Q, ⌘Q racing red close)
resolve to exactly one guard decision. Confirmed structurally this milestone
(`! grep -q "PredefinedMenuItem::quit" desktop/src-tauri/src/menu.rs` in the master gate) and via the
existing re-entrancy regression tests, still green.

## Security

Re-verified this milestone, 0 deviations:

- WebView shell/process/broad-filesystem permission: **NO**.
- WebView capability: exactly `["core:default", "dialog:allow-open", "dialog:allow-save",
  "core:window:allow-destroy"]`.
- CSP: unchanged — `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost`.
- IPC: private stdin/stdout, no network surface.
- Rust owns the sidecar lifecycle end to end.
- Remote services / external CDN: **NONE**.
- Native menu integration introduced no new WebView-facing capability — menu construction/dispatch
  is entirely Rust-side.

## Performance

No regression found. Warm timings from this milestone's own real end-to-end run against the freshly
rebuilt sidecar: preview (model + tessellation) ~0.12–0.15 s, export ~0.13–0.14 s — consistent with
the Build 023/024 baseline. No new perf-optimization work was undertaken (not in scope; no regression
evidence to act on).

## Memory

No new endurance testing performed this milestone (not in scope; Build 024 M3's bounded 20-export
measurement — +5.07% RSS, tapering, no leak — stands and was not invalidated by any Build 025
change).

## Packaging

`scripts/build-productive-desktop-app.sh release`: PyInstaller onedir sidecar, Tauri release build,
hash-gated post-bundle dylib dedup, no onefile fallback. Clean rebuild this milestone:

| Metric | Value |
|---|---|
| Bundle size (`du -sh`) | 287 MiB |
| Bundle size (exact, file bytes only) | 299,992,897 bytes (~286.1 MiB) |
| Files | 201 |
| Directories | 57 |
| Symlinks | 77 |
| Mach-O binaries | 161 |

Compared against Build 024 M4's own measurement (299,743,617 bytes / ~285.86 MiB / 201 files / 57
dirs / 77 symlinks): +249,280 bytes (+0.08%), fully explained by the new project-persistence, report,
and native-menu code added across Build 025 M1–M4. No unexpected large delta.

## Dependency Invariants

Meaningful detection (filename-glob search across the freshly rebuilt bundle, excluding the
`cadquery_ocp_novtk` false-positive substring match) confirms:

| Dependency | Count |
|---|---|
| VTK | 0 |
| PySide6 | 0 (productive bundle) |
| Qt | 0 |
| numba | 0 |
| llvmlite | 0 |
| scipy | 0 |

## Repository Cleanup

Full record: `docs/migration/BUILD-025-M5-REPOSITORY-CLEANUP.md`. Summary: a systematic discovery
pass (stale-marker grep, dead-frontend/Rust/Python-code cross-reference, validation- and
build-script inventory, duplicate/stale-filename search, `git ls-files` generated-artifact check,
documentation-staleness check) found **0 `SAFE_TO_REMOVE` candidates** — Builds 022–025 each closed
with their own integration gate, so the repository never accumulated cleanup debt. The real cleanup
work this milestone was documentation synchronization: `BUILD-025-M1-HUMAN-VALIDATION.md` (was still
`PENDING` despite M2–M4 having since built on top of an already-passed M1), `BUILD-025-M4-HUMAN-VALIDATION.md`
(recorded PASS per this mandate's own explicit authorization), and `README.md`/`ROADMAP.md`/
`docs/migration/README.md` (all still read "Build 025 IN PROGRESS"). One dead-field removal was made
as a narrow, evidence-based integration fix (not a feature change): the sidecar `status` command's
`milestone` field (`src/zerorod_sidecar/main.py`) was a hardcoded, never-updated `"build023-m1"`
string, silently diverging from the single authoritative build-identity source
(`desktop/src-tauri/src/commands.rs`'s `app_info()`); removed from the sidecar protocol, the
TypeScript `SidecarStatus` type, and both call sites' tests rather than perpetually re-synchronized,
since nothing productive consumed it (Diagnostics renders build/milestone identity exclusively from
`app_info()`). `desktop/src-tauri/src/commands.rs`'s own `app_info()` milestone constant was bumped
`"M4"` → `"M5"`, per this build's own build-identity convention. Legacy PySide6 modified: **NO**.

## Test Summary

Clean run against this milestone's own HEAD:

- **Python**: 380 passed, 1 skipped (pre-existing, unrelated TE-001 Gate-A re-evaluation note).
  Ruff clean.
- **Rust**: 59/59 passed (summed across all test binaries). `cargo fmt --check` /
  `cargo clippy --all-targets -- -D warnings` clean.
- **Frontend**: 369 passed across 22 of 23 test files (1 file skipped, pre-existing). TypeScript
  clean. Production build clean.

## Artifact Identity

| Proof | Value |
|---|---|
| Commit | `195abb5392509af511d3973dc7d016312f1baa7e` (Build 025 M4 final, M5 branch point) |
| Frontend asset filename | `index-DJRwSsH-.js` |
| Frontend asset SHA-256 | `69ce34979246ed832abad86c056d358f3c0ef2ec71e88ad527768aaad01b5506` |
| Compiled Build-025-M5 marker | `M5` (exactly 1 occurrence in the compiled binary's string table — the `app_info()` milestone constant) |
| Native menu marker | menu item ids/labels present in the compiled binary (`view-reset`/`Reset View`, `view-body`/`Show Body`, `view-strings`/`Show Strings`, `view-report`/`Instrument Report`, `Diagnostics`) |
| Project-persistence marker | `project_open`/`project_save` sidecar commands present and exercised end to end in the master gate's real roundtrip |
| Deterministic bundle fingerprint | `2da09b377fc4cac7f3933dc4413ebcc253d49b85959ab6bda595b8283a5462eb` (aggregate SHA-256 over sorted relative paths, per-file content SHA-256, and symlink targets) |

## Known Limitations

Carried forward from Build 024, reclassified where Build 025 changed their status:

1. Real sidecar-crash-during-request and real request-timeout remain CODE-INSPECTED, not empirically
   tested — **STILL_VALID**, unchanged since Build 024.
2. Real OS-level disk-full remains NOT SAFELY TESTABLE; only the error-mapping boundary is verified
   (SIMULATED) — **STILL_VALID**.
3. STEP export is not byte-identical across repeated identical-parameter exports (believed cosmetic,
   internal entity numbering) — **STILL_VALID**, not independently re-verified this milestone.
4. No STL/STEP format-level structural sanity check beyond the existing non-empty-file check —
   **STILL_VALID**.
5. Long destination-path testing was not separately exercised — **STILL_VALID**.
6. Project persistence, full desktop feature parity — **SUPERSEDED**: implemented in Build 025
   M1–M4 (project persistence, lifecycle, preview/report parity, native shell), within the
   Project-Owner-approved M1–M4 milestone plan.
7. Real `muda`/AppKit native menu *construction* cannot be exercised under `cargo test` (no Cocoa
   main thread in the test harness) — **STILL_VALID** (Build 025 M4's own, newly-documented
   limitation), compensated by structural source checks, a real dev-mode launch, and compiled-binary
   `strings` evidence; not independently testable any other way without a full UI-automation harness,
   which is out of scope.
8. Settings, Recent Files, drag & drop, file associations/Finder integration, and accessibility —
   **DEFERRED**: the original Build 025 Discovery scope (`BUILD-025-GAP-REPORT.md`) named these as
   candidate Build 025 surface, but the Project-Owner-approved M1–M4 milestone plan
   (`BUILD-025-HANDOFF.md`'s "what Build 025 owns") scoped Build 025 down to project persistence,
   lifecycle polish, preview/report parity, and the desktop shell. Not a regression or an oversight —
   an explicit scope decision at milestone-planning time, carried forward as open product surface
   for a later, explicitly authorized build.
9. Signing/notarization — **DEFERRED** to Build 026, unchanged.

## Explicit Non-Scope (this milestone)

Per the M5 mandate, none of the following were done, added, or reopened in M5: new project/preview/
export/report/menu feature, new Settings system, Recent Files, drag & drop, file associations, Open
With/Finder integration, updater, signing, notarization, PySide6 retirement, or starting Build 026.

## Next Build Handoff

Full handoff: `docs/migration/BUILD-026-HANDOFF.md`. Build 026 inherits a working, tested, packaged,
human-validated desktop application — project persistence, a productized lifecycle, preview/report
parity, and a native macOS shell — on top of the Build 022–024 foundation, and picks up Production
Packaging & macOS Integration (production bundle hardening, final dependency audit, performance
baseline, signing/notarization preparation, release workflow) per the existing `ROADMAP.md`
build-sequence table — no new scope invented here.
