# Build 025 — Gap Report

Discovery document, produced before any Build 025 implementation. Synthesizes
`BUILD-025-FEATURE-PARITY-MATRIX.md`, `BUILD-025-LIFECYCLE-ANALYSIS.md`,
`BUILD-025-PROJECT-PERSISTENCE-ANALYSIS.md`, and `BUILD-025-DESKTOP-INTEGRATION-ANALYSIS.md` into
one view of how large Build 025 actually is, organized by the mandate's required structure (§42).

## Already Complete

Real, evidence-confirmed parity or better, requiring no Build 025 work:

- All 16 `zerorod-parameters/v1` fields editable, grouped, validated, with Reset — **exceeds**
  legacy's 11-of-16 coverage.
- Live, debounced preview regeneration with stale-response protection — functionally equivalent
  design (both independently converged on a generation-counter pattern).
- Rotate, zoom, and camera-fit-on-load — **exceeds** legacy (real 3D via `OrbitControls`, which
  also provides pan; legacy has no pan).
- STL/STEP/report export with native directory dialog, overwrite preflight, two-layer result
  verification — **exceeds** legacy (no preflight/overwrite-confirmation/structural-verification in
  the legacy app at all).
- Sidecar lifecycle: lazy spawn, timeout, crash-detect-and-restart-once, graceful shutdown with a
  forced-kill fallback on app exit — already meets the mandate's "no orphan process" bar, already
  human-validated across Build 022.
- Accessible form semantics (explicit `<label for>`, `aria-describedby`, `aria-invalid`,
  `role="alert"`/`role="alertdialog"`) — **exceeds** legacy's implicit Qt accessibility bridge.
- ⌘Q Quit — native, already triggers sidecar shutdown via `ExitRequested`.
- Application metadata registered with the OS (`productName` in `tauri.conf.json`).

## Required for Parity

Real legacy capabilities with no current Tauri equivalent, justified by direct evidence (not
copied blindly — each was checked against whether legacy's own behavior is worth reproducing):

1. **Project persistence**: New, Open, Save, Save As, reusing the existing `.zerorod`/`project.py`
   format unmodified. The single largest item in this list — genuinely new IPC/UI/security surface,
   not a boundary-exposure exercise (Project Persistence Analysis §2).
2. **Reset/fit view control** — legacy's explicit "Reset View" button has no Tauri equivalent
   beyond an automatic extreme-bounds-change heuristic.
3. **Body/Rod/Strings visibility toggles** — legacy's three checkboxes have no Tauri equivalent at
   all.
4. **Automatic initial preview load** — closing the "empty viewport at first launch" gap (Lifecycle
   Analysis §1); legacy always shows a model immediately, Tauri currently requires a manual click.
5. **Live "Instrument Report" view** — legacy's continuously-updated Markdown report tab has no
   Tauri equivalent; `build_report()` already exists, unmodified, engine-side.
6. **Native File menu** (New/Open/Save/Save As/Export/Quit) and **Help menu** (Diagnostics, About) —
   no native menu exists in Tauri today at all.
7. **⌘N/⌘O/⌘S/⇧⌘S shortcuts** — meaningless until #1 exists, but real parity items once it does.
8. **About dialog** — legacy has one; Tauri has none. Low effort, no engine dependency.
9. **Diagnostics view** — legacy has a dedicated dialog; Tauri's equivalent data is scattered across
   product-UI debug buttons rather than presented as diagnostics (this item is listed here and
   under "Internal/Diagnostics Only" below because it is simultaneously a required-parity target
   *and* the vehicle for relocating existing technical controls — see that section).

## Needs Tauri Redesign

Real legacy capability where a literal port would be wrong for the new architecture/UX, requiring
a Tauri-appropriate reimplementation rather than a copy:

- **Startup failure UX** — legacy's `QMessageBox.critical` pattern is a reasonable *concept*
  (friendly message + log/details access), but the actual mechanism must be new frontend UX built
  against `EngineError`, not a Qt dialog port.
- **"Open Documentation" menu item** — legacy opens a repo-relative `docs/INSTALL_MACOS.md`, which
  will not exist at a packaged `.app`'s runtime path; needs its own design if pursued.
- **Rendering style** — already redesigned in Build 022 M3 (real WebGL vs. `QPainter` projection);
  recorded here for completeness, not as outstanding work.
- **Toolbar** — legacy's `QToolBar` maps to *some* Tauri-appropriate UI affordance for quick
  actions, but not necessarily a literal toolbar; the underlying actions (New/Open/Save/Export) are
  the actual parity requirement, the toolbar widget is a layout choice.

## Internal/Diagnostics Only

Genuinely useful, but does not belong in the primary product UI — the mandate's central "no
development console in the product UI" principle applies directly:

- The 5-row technical status panel (`Desktop shell`/`Rust bridge`/`Python sidecar`/`CAD
  engine`/`3D preview`).
- "Start / Check Engine" and "Ping Engine" buttons and the raw JSON they surface.
- "Request Preview Data" button (self-documented as non-rendering).
- The free-text "last action" log.
- pid, ping latency, sidecar version/variant info — real diagnostic value, relocated rather than
  deleted (Lifecycle Analysis §3, Desktop Integration Analysis §5).

## Obsolete Legacy Behavior

Legacy behavior that should explicitly **not** be copied, because it is a gap or oversight in
legacy itself, not a designed feature worth preserving:

- **No dirty-state tracking / no unsaved-changes warning on close or quit** — confirmed absent by a
  full read of `main_window.py` (no `isWindowModified`, no `closeEvent` override). A silent
  data-loss behavior, not a pattern to reproduce (Project Persistence Analysis §3/§5).
- **`.zerorod` file-type registration that doesn't actually work** — declared in
  `packaging/macos/ZeroRodCAD.spec`'s `Info.plist` but never wired to actual file-open handling in
  `app.py`/`main_window.py`. Do not treat this as "already implemented."
- **`--diagnose`/`--startup-test` CLI flags** — a packaged `.app` has no natural CLI entry point a
  user reaches for; superseded by an in-app Diagnostics view.
- **Manual "Engine starten"-style controls** — the mandate explicitly calls this pattern out as
  obsolete for the new architecture (§6 example); the closest Tauri analogs ("Start / Check
  Engine", "Ping Engine") are exactly this pattern and are classified accordingly above.

## Deferred

Real or plausible capabilities with legitimate reasons to postpone — evidenced, not just
convenient:

- **Drag & drop project files** — real legacy behavior, low risk, but sequenced after Open exists
  (reuses its logic rather than building a parallel path).
- **Recent files** — legacy doesn't have this either; a macOS convention, not a parity requirement.
- **Window geometry persistence** — legacy doesn't have this either; would need a new
  plugin/dependency, a real packaging-impact question, not free.
- **Working file-association / "Open With"** — legacy's declaration is non-functional, so building
  a *working* version would be new functionality exceeding legacy, not parity; worth a deliberate
  cost/benefit decision, not silent inclusion.
- **⌘E Export shortcut, ⌘Z/⇧⌘Z Undo/Redo** — legacy never had either; not required parity.
- **"Reveal in Finder" after export** — neither app has this; small future nicety.
- **File-level logging to disk** — legacy has it; unclear it adds value beyond the Diagnostics view
  once that exists; low urgency either way.

## Decision Required

Points where evidence conflicts, is genuinely ambiguous, or depends on a design choice this
discovery cannot make unilaterally:

- **Startup failure UX exact design** (message wording, Retry/Show Details/Quit affordances) —
  Lifecycle Analysis §5.
- **Engine-state model granularity** — whether the existing coarse `LifecycleState`
  (`Stopped`/`Running`/`Error`) needs to become finer-grained; recommendation is "not
  speculatively," pending what the Diagnostics/failure-UX design concretely needs — Lifecycle
  Analysis §8.
- **View menu existence** — only relevant if Reset View/layer-visibility controls become menu items
  rather than inline preview buttons; a UI-layout choice.
- **⌘, Preferences shortcut / any Settings surface beyond "remembered last directory"** — legacy
  provides no evidence a broader Settings surface is needed; only relevant if one gets built anyway
  for other reasons — Desktop Integration Analysis §3.
- **Whether opening a project should silently discard a dirty in-memory draft (matching legacy) or
  prompt** — a genuine design choice, not resolvable from evidence alone — Project Persistence
  Analysis §9.
- **Exact new sidecar command names/shapes for project save/load** — a boundary-exposure design
  decision for the implementing milestone.
- **File-level logging to disk** — also listed under Deferred; whether it's worth building at all
  is genuinely undecided, not a clear "no."
- **Focus order / focus-visible audit outcome** — needs a real interactive check, not a code-only
  judgment.

## How big is Build 025, actually?

Of the 54 rows evaluated in the Feature Parity Matrix: 21 already match or exceed legacy (no work),
16 are real required-parity gaps, 5 need a Tauri-appropriate redesign rather than a port, 2 are
internal/diagnostics-only relocations, 7 are legacy behaviors explicitly not worth copying, 10 are
legitimately deferred, and 8 remain open design decisions.

The substantive new-build surface clusters into four coherent areas, in the dependency order the
analyses above establish (Project Persistence is a prerequisite for menus/shortcuts, per
`BUILD-025-HANDOFF.md`'s own observation):

1. **Project Persistence** (New/Open/Save/Save As, dirty-state model, native file dialogs) — the
   largest, most novel piece; a real new IPC/UI/security surface.
2. **Product-UI cleanup** (relocate technical controls into Diagnostics, automatic initial preview
   load) — small in code size, high in product-quality impact, and low-risk since it touches no
   engine/protocol code.
3. **Preview parity** (Reset/fit view control, layer-visibility toggles) — small, self-contained,
   no protocol change.
4. **Desktop shell** (native menus, shortcuts, About dialog, Diagnostics view) — depends on #1 for
   File-menu items to have something to bind to, and benefits from #2's relocation work already
   having identified what Diagnostics needs to contain.

The "Instrument Report" live view (Parameters section of the matrix) is a smaller, largely
independent fifth item — it depends on nothing above and could be sequenced anywhere.

No item identified anywhere in this discovery requires a protocol version bump, a new CAD kernel, a
renderer change, a process-model change, or any other architecture-guardrail violation (mandate
§49) — everything above is additive within the existing Tauri v2 + Rust + persistent-sidecar +
Three.js architecture.
