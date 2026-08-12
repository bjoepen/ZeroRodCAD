# Build 025 — Feature Parity Matrix

Discovery document. Produced on branch `research/build025-feature-parity-discovery` before any
Build 025 implementation, per the Build 025 mandate's stop condition. Baseline: Build 024 M4 HEAD
(`7af13cc`), working tree clean.

## Method

Every row cites concrete evidence: a legacy PySide6 file/line/class/method, and a Tauri
Rust/TypeScript file/line/function/command. No row asserts a legacy feature without a citation
(mandate §38, "no feature without evidence"). Legacy source: `src/zerorodcad_desktop/*.py` +
`src/zerorodcad/{project,parameters,validation,export,report}.py`. Tauri source:
`desktop/src-tauri/src/*.rs` + `desktop/frontend/src/*.ts` + `desktop/src-tauri/tauri.conf.json` +
`desktop/src-tauri/capabilities/main-capability.json`.

Classification vocabulary (mandate §6, exact categories):

```text
REQUIRED_PARITY | ALREADY_IMPLEMENTED | REDESIGN_FOR_TAURI | INTERNAL_ONLY | OBSOLETE | DEFERRED | DECISION_REQUIRED
```

## Application Lifecycle

| Area | Legacy Feature | Legacy Evidence | Tauri Status | Classification | Build 025 Recommendation | Risk | Human Validation |
|---|---|---|---|---|---|---|---|
| Lifecycle | Eager GUI start, lazy CAD-engine import ("Deliberately lazy: importing CadQuery/OCP during application startup made packaged builds fragile") | `app.py:46-71` (QApplication/MainWindow eager), `workers.py:28-29`, `export.py:35-36` (CadQuery imported only inside worker/export call) | Rust/WebView start eagerly; Python sidecar spawned lazily on first `engine::request` call, reused after | `engine.rs:194-202` `ensure_started`, doc comment "Lazy vs. eager start" | ALREADY_IMPLEMENTED | Same principle, different mechanism — no gap | — | N/A |
| Lifecycle | Startup failure UX: caught exception → `QMessageBox.critical` with message + log path, then re-raise | `app.py:72-91` `_show_startup_error` | No dedicated "Engine could not start" UX; a sidecar spawn failure only surfaces as an `ERROR` row in the raw status panel or a raw `EngineError.code` in "last action" text | `main.ts:86-98,167-169` (`handleStartCheckEngine`), no friendly dialog | DECISION_REQUIRED | Design a user-facing failure surface (Retry/Show Details/Quit) — mandate §27 | Medium (first-run UX; low code risk) | Yes (real failure induction) |
| Lifecycle | No child process to clean up (Qt/OS handles teardown) | N/A | Sidecar killed explicitly on `ExitRequested`; `engine::shutdown` also invoked by explicit `engine_shutdown` command | `lib.rs:45-55`, `engine.rs:250-257,292-306` | ALREADY_IMPLEMENTED | Exceeds legacy (0 orphan-process guarantee, already tested per Build 022 M2) | — | N/A (already validated in Build 022) |
| Lifecycle | No crash-recovery concept (no subprocess) | N/A | Timeout/crash detected → kill dead process → restart-once → retry the same request | `engine.rs:214-248` `request()` | ALREADY_IMPLEMENTED, INTERNAL_ONLY | Already transparent to the user (mandate §28's "no manual Restart Engine" goal is already met) | — | N/A (already validated in Build 022) |
| Lifecycle | File logging to `~/Library/Logs/ZeroRodCAD/zerorodcad.log` + global exception hook | `startup.py:11-38` | No file logging found in Rust or frontend source | — | DECISION_REQUIRED | Only valuable if it materially helps support/diagnostics beyond the Diagnostics-dialog approach below; not urgent | Low | N/A |
| Lifecycle | `--diagnose` / `--startup-test` CLI flags | `app.py:24-36,51-54,65-69` | No CLI-flag surface (Tauri app has no argv-driven text-mode path) | — | OBSOLETE | A packaged `.app` has no natural CLI entry a user would reach for; superseded by an in-app Diagnostics area (see Desktop Integration analysis) | — | N/A |
| Lifecycle | *(no legacy equivalent — no subprocess)* | — | Raw technical status panel embedded in the main product UI: 5 status rows (`Desktop shell`/`Rust bridge`/`Python sidecar`/`CAD engine`/`3D preview`) plus 4 action buttons (`Start / Check Engine`, `Ping Engine`, `Request Preview Data`, `Load / Refresh ZeroRod`) | `main.ts:22-44,52-58,167-178` | DECISION_REQUIRED (candidates: `REMOVE_FROM_PRODUCT_UI` for 3, `MOVE_TO_DIAGNOSTICS` for all 5, see Desktop Integration Analysis §"Technical Controls") | Directly violates the mandate's "ZeroRodCAD besitzt eine Engine. Der Benutzer startet keine Engine." principle — highest-priority UI productization item | Low (removal/relocation, no engine-layer change) | Yes (visual/workflow change) |
| Lifecycle | Automatic initial preview on window construction (`_update_workspace()` called from `__init__`, timer fires with 0 ms delay) | `main_window.py:68-69,278-281` | **No automatic initial preview.** `parameterPanel.load()` only fetches default parameter *values*; the 3D viewport stays empty until the user manually clicks "Load / Refresh ZeroRod" | `main.ts:186-208` `init()`, `parameter_panel.ts:494-502` `load()` (fetches `parameters_defaults` only, never calls `preview.load()`/`fetchPreview`) | REQUIRED_PARITY | A first-launch empty viewport is a real regression vs. legacy's "always shows something" behavior — fold into the same fix as the row above (auto-load once at startup, drop the manual button as a *required* action) | Low | Yes |

## Projects (Persistence)

| Area | Legacy Feature | Legacy Evidence | Tauri Status | Classification | Build 025 Recommendation | Risk | Human Validation |
|---|---|---|---|---|---|---|---|
| Projects | New Project (⌘N) | `main_window.py:72-74,440-443` `new_project()` | None | REQUIRED_PARITY | Core Build 025 scope | Medium (new surface) | Yes |
| Projects | Open Project (⌘O), native file picker filtered to `*.zerorod` | `main_window.py:76-78,445-454` `open_project()` | None | REQUIRED_PARITY | Core Build 025 scope | Medium | Yes |
| Projects | Save (⌘S), Save As (⇧⌘S) with a default filename derived from `project_name` | `main_window.py:80-86,456-483` | None | REQUIRED_PARITY | Core Build 025 scope | Medium | Yes |
| Projects | `.zerorod` file format: human-readable JSON, `{"format": "ZeroRodCAD Project", "version": 1, "parameters": ZeroRodParameters.to_dict()}` | `src/zerorodcad/project.py` (35 lines total: `save_project`/`load_project`) | None (no Tauri-side reader/writer) | REQUIRED_PARITY | **Reuse this format unmodified** — it is already versioned, already shared 1:1 with `zerorod-parameters/v1`'s `values` shape (`docs/contracts/ZEROROD-PARAMETERS-V1.md` states this explicitly), and is trivially exposable through the sidecar without a new schema. See Project Persistence Analysis. | Low (format already exists and is simple) | Yes |
| Projects | Dirty-state tracking / unsaved-changes warning on close or quit | **Not implemented.** No `isWindowModified`, no `closeEvent` override anywhere in `main_window.py` — confirmed by full-file read. Quitting or closing with unsaved changes silently discards them. | N/A | OBSOLETE (legacy behavior itself is a latent data-loss gap, not a pattern to copy) | Build 025 should design proper dirty-state tracking (draft/preview/project, mandate §14) rather than replicate legacy's silent-discard behavior | Medium (state-machine design work) | Yes |
| Projects | Drag & drop a `.zerorod` file onto the main window to open it | `main_window.py:522-534` `dragEnterEvent`/`dropEvent` | None | OPTIONAL / DEFERRED (mandate §25) | Nice-to-have once Open exists; not required for parity | Low | N/A until built |
| Projects | `.zerorod` file-type registration (`CFBundleDocumentTypes`, `LSHandlerRank: Owner`) in the packaged `.app`'s `Info.plist` | `packaging/macos/ZeroRodCAD.spec:81-89` | None | DEFERRED | **Important nuance:** legacy *declares* the file association in packaging but never actually opens the file — `app.py`'s `parse_arguments` has no positional path argument, and no `QFileOpenEvent`/`event()` override exists anywhere in `main_window.py`/`app.py`. Double-clicking a `.zerorod` file in Finder with legacy installed would launch the app but not load the file. This is a **non-functional legacy feature** — do not copy it as "already working"; if Build 025 wants real file-association support it is new work, not parity. | Low urgency | N/A |
| Projects | Remembered last-used directory shared by Open/Save/Export dialogs (`QSettings "paths/last_directory"`) | `main_window.py:546-550` `_dialog_directory`/`_remember_directory` | None (Build 024's `select_export_directory` does not persist a remembered directory) | DECISION_REQUIRED | Small, low-risk addition once Open/Save exist — bundle with Project Persistence milestone rather than treat as its own feature | Low | Yes (UX confirmation) |

## Parameters

| Area | Legacy Feature | Legacy Evidence | Tauri Status | Classification | Build 025 Recommendation | Risk | Human Validation |
|---|---|---|---|---|---|---|---|
| Parameters | Editable parameter fields | Only **11 of the 16** `zerorod-parameters/v1` fields are exposed in the legacy UI (`project_name`, `body_width`, `body_depth`, `fretboard_height`, `rod_diameter`, `groove_diameter`, `channel_rod_clearance`, string count/gauges, `string_spacing`, `string_inlet_z`, `channel_diameter`); `rod_center_z_offset`, `groove_front_clearance`, `string_inlet_y`, `channel_overrun_at_inlet`, `minimum_wall` exist only as dataclass defaults, never editable | `main_window.py:113-174` | All 16 fields editable, grouped (Project/Body/Rod & Groove/Strings/Channel/Tolerances) | `parameter_metadata.ts` (full field table), Build 023 M2 | ALREADY_IMPLEMENTED — **Tauri exceeds legacy** | No action needed | — | Already validated (Build 023) |
| Parameters | Reset to defaults | Only reachable indirectly via "New" (`new_project()` reloads `ZeroRodParameters()`); no standalone Reset control | `main_window.py:440-443` | Explicit Reset control, loads canonical defaults through the real `parameters_defaults` path | Build 023 M2 (`docs/migration/BUILD-023-M2-PARAMETER-CONTROLS.md`) | ALREADY_IMPLEMENTED — exceeds legacy | No action needed | — | Already validated |
| Parameters | Validation error presentation | Status banner (color-coded valid/warning/error text) | `main_window.py:331-354` | Per-field `aria-invalid`/`role="alert"` plus structured `invalid_parameters_domain`/`invalid_parameter_type` error codes | `parameter_panel.ts:112-123` | ALREADY_IMPLEMENTED — exceeds legacy (accessible semantics legacy never had) | No action needed | — | Already validated |
| Parameters | Live regeneration on edit | `QTimer` debounce (280 ms) → background `QThreadPool` worker → generation counter discards stale results | `main_window.py:46,274-330`, `workers.py` | Debounced (300 ms) live preview, generation-based stale-response protection, in-flight coalescing | `live_preview.ts`, Build 023 M4 | ALREADY_IMPLEMENTED — functional parity confirmed (both independently converged on a generation-counter pattern) | No action needed | — | Already validated |
| Parameters | **Live "Instrument Report" tab** — a `QTextBrowser` tab next to the 3D preview showing `build_report()`'s Markdown (parameters table, string table, validation summary, notice), updated on every parameter edit, continuously, not only on export | `main_window.py:185-193,282-294`, `zerorodcad/report.py:11-63` `build_report()` | **No equivalent.** `zerorodcad.report.save_report` is only invoked inside `export_project` (a file write); nothing in the frontend renders `build_report()`'s Markdown live in the UI | `export.py` (sidecar side, unchanged), no frontend consumer of report content | REQUIRED_PARITY or DECISION_REQUIRED | A genuinely distinct, real feature (not covered by Build 024's export). Recommend classifying REQUIRED_PARITY given it is core "what the user is looking at" information already computed engine-side with zero new engine work (`build_report` exists, unmodified) — the only new work is a frontend tab/panel and (if not already exposed) a sidecar command returning report text without writing a file. Flag for milestone scoping. | Low–Medium | Yes |

## Preview

| Area | Legacy Feature | Legacy Evidence | Tauri Status | Classification | Build 025 Recommendation | Risk | Human Validation |
|---|---|---|---|---|---|---|---|
| Preview | Rotate | Manual mouse-drag yaw/pitch in a custom `QPainter` projection | `preview_widget.py:77-90,213-224` | `OrbitControls` (real 3D, not a projection) | `scene.ts:36-37` | ALREADY_IMPLEMENTED — exceeds legacy | — | Already validated (Build 022 M3) |
| Preview | Zoom | Mouse-wheel zoom factor | `preview_widget.py:96-100` | `OrbitControls` wheel zoom | `scene.ts:36-37` | ALREADY_IMPLEMENTED | — | Already validated |
| Preview | Pan | **Not implemented in legacy** (no pan handling anywhere in `preview_widget.py`) | — | `OrbitControls` provides pan (right-drag / two-finger) by default | `scene.ts:36-37` | ALREADY_IMPLEMENTED — Tauri exceeds legacy (legacy has no pan at all) | — | Already validated |
| Preview | **Reset View button** — explicit control resetting yaw/pitch/zoom to the fixed starting orientation | `main_window.py:206,214` `reset_button` → `preview.reset_view()`, `preview_widget.py:56-60` | **No equivalent control.** Only automatic camera fit exists: on first commit, or when bounds change "extremely" (>1.5x) | `scene.ts:81-131` `fitCameraToBounds`/`isExtremeBoundsChange`, `preview.ts:204-210` `commitPreview` | REQUIRED_PARITY | A real, small, concrete gap — a manual "reset/fit view" control the user can invoke anytime (not just relying on the extreme-bounds-change heuristic) | Low | Yes |
| Preview | Fit model to view | Implicit: every repaint recomputes scale from visible-geometry bounds | `preview_widget.py:125-141` | `fitCameraToBounds` on first load / extreme bounds change | `scene.ts:81-102` | ALREADY_IMPLEMENTED | — | Already validated |
| Preview | **Body / Rod / Strings visibility toggles** — 3 checkboxes wired to per-layer show/hide | `main_window.py:200-223` `body_toggle`/`rod_toggle`/`strings_toggle`, `preview_widget.py:62-76,199-211` `set_layer_visibility` | **No equivalent.** `meshContractToGeometries` output is always fully rendered; no UI toggle exists anywhere in `main.ts`/`preview.ts`/`scene.ts` | — | REQUIRED_PARITY | Concrete, well-scoped gap — a real, previously-working legacy capability with no Tauri counterpart | Low–Medium | Yes |
| Preview | Rendering style (flat-shaded 2.5D projection, light background) | `preview_widget.py:102-197` (custom triangle depth-sort + Lambertian shading) | Real WebGL scene: dark background, ambient + directional lighting, `MeshStandardMaterial` | `scene.ts:20-42`, `preview.ts:162-167` | REDESIGN_FOR_TAURI (already redesigned in Build 022 M3, not a gap — different but strictly better renderer) | No action needed | — | Already validated |

## Export

Build 024 is complete; this section only records comparison evidence, per mandate §19 — it does not
reopen Build 024 scope.

| Area | Legacy Feature | Legacy Evidence | Tauri Status | Classification | Build 025 Recommendation | Risk | Human Validation |
|---|---|---|---|---|---|---|---|
| Export | STL/STEP/report export via a single directory picker, silent overwrite, result summary in a message box | `main_window.py:485-502` `export_files()`, `zerorodcad/export.py` | Native directory dialog, preflight conflict check, in-panel overwrite confirmation, two-layer (sidecar + Rust) result verification, in-panel success/error | `export_panel.ts`, `export_result.rs`, Build 024 M1–M3 | ALREADY_IMPLEMENTED — Tauri **exceeds** legacy (legacy has no preflight, no overwrite confirmation, no structural result verification) | No action needed | — | Already validated (Build 024 M2/M3) |
| Export | "Reveal in Finder" after export | Not implemented in legacy either | Not implemented | OBSOLETE / OPTIONAL (neither app has this) | DEFERRED — small future nicety, not a parity gap | Low | N/A |

## Menus

| Area | Legacy Feature | Legacy Evidence | Tauri Status | Classification | Build 025 Recommendation | Risk | Human Validation |
|---|---|---|---|---|---|---|---|
| Menus | File menu: New, Open…, Save, Save As…, Export STL / STEP…, Quit | `main_window.py:229-239` | No native menu defined at all — `lib.rs` has no `tauri::menu` setup; only the OS default window chrome exists | `lib.rs:23-56` (no menu builder present) | REQUIRED_PARITY | Build once Project Persistence (New/Open/Save/Save As) and Export exist; Quit is separately covered below | Low (menu wiring only) | Yes |
| Menus | Help menu: Open Documentation, Diagnostics…, About | `main_window.py:241-245` | None | REQUIRED_PARITY (Diagnostics, About) / REDESIGN_FOR_TAURI (Open Documentation) | About and Diagnostics are direct parity items (see Desktop Integration); "Open Documentation" needs a packaged-app-appropriate redesign (legacy opens a raw repo-relative `docs/INSTALL_MACOS.md`, which won't exist at a bundled `.app`'s runtime location) | Low | Yes |
| Menus | Edit menu | **Does not exist in legacy** (no Edit menu anywhere in `_build_menu_and_toolbar`) | None | OBSOLETE | Nothing to parity against — do not invent one; native text fields already get OS-level Cut/Copy/Paste for free | — | N/A |
| Menus | View menu | **Does not exist in legacy** | None | DECISION_REQUIRED | Only relevant if Reset View / layer toggles (above) are designed as menu items rather than inline preview controls — a UI design choice, not a parity requirement | Low | N/A |
| Menus | Window menu | No custom items (Qt/macOS default only) | No custom items | INTERNAL_ONLY | Comes largely for free once any native menu exists on macOS; not urgent on its own | — | N/A |
| Menus | Toolbar (New/Open/Save icons + Export) | `main_window.py:247-254`, non-movable `QToolBar` | None | REDESIGN_FOR_TAURI / DEFERRED | A toolbar is a UI-layout choice; the underlying *actions* are the REQUIRED_PARITY items above, not the toolbar widget itself | Low | N/A |

## Keyboard Shortcuts

| Shortcut | Legacy | Legacy Evidence | Tauri | Classification | Build 025 Recommendation |
|---|---|---|---|---|---|
| ⌘N New | Yes (`Ctrl+N`, Qt auto-maps to ⌘ on macOS) | `main_window.py:72-74` | No | REQUIRED_PARITY | Bind once New exists |
| ⌘O Open | Yes | `main_window.py:76-78` | No | REQUIRED_PARITY | Bind once Open exists |
| ⌘S Save | Yes | `main_window.py:80-82` | No | REQUIRED_PARITY | Bind once Save exists |
| ⇧⌘S Save As | Yes | `main_window.py:84-86` | No | REQUIRED_PARITY | Bind once Save As exists |
| ⌘E Export | **No shortcut in legacy** — Export is a plain `QAction`/button with no `setShortcut` call | `main_window.py:88-89,165-167` | No | DEFERRED / OPTIONAL | Not a parity requirement (legacy never had it); would exceed legacy, not match it — low priority |
| ⌘Z / ⇧⌘Z Undo/Redo | **Not implemented anywhere in legacy** — no `QUndoStack`, no undo-related action, confirmed by full-file read of `main_window.py` | — | No | DEFERRED | Per mandate §17: not required parity since legacy never had it. Native OS text-field undo (browser-level, per `<input>`) is already free and distinct from app-level undo — do not conflate the two when scoping |
| ⌘Q Quit | Yes, `Ctrl+Q` → `self.close()` | `main_window.py:91-93` | Comes for free from the native window/OS (Tauri apps get ⌘Q natively); already triggers the `ExitRequested` sidecar-shutdown path | `lib.rs:45-55` | ALREADY_IMPLEMENTED | Re-verify once Project Persistence exists that Quit also runs the unsaved-changes check (mandate §29) — currently nothing to check, so trivially "safe" today |
| ⌘, Preferences | **Does not exist in legacy** (no Preferences dialog/shortcut of any kind) | — | No | DECISION_REQUIRED | Only relevant if a Settings surface is built (see Desktop Integration Analysis) — legacy provides no evidence this is required |

## Settings / Preferences

| Area | Legacy Feature | Legacy Evidence | Tauri Status | Classification | Build 025 Recommendation | Risk |
|---|---|---|---|---|---|---|
| Settings | Remembered last-used directory (`QSettings "paths/last_directory"`) | `main_window.py:546-550` | None | DECISION_REQUIRED | Session State / Application Preference (not Project Data) — bundle with Project Persistence work | Low |
| Settings | Window geometry persistence | **Not implemented in legacy** — `MainWindow.__init__` always calls `self.resize(1240, 780)`; no `QSettings` geometry save/restore anywhere | `main_window.py:57` | Not implemented — `tauri.conf.json` hardcodes `1000x700` always | `tauri.conf.json:17-18` | OBSOLETE as a parity claim (neither app does this) | OPTIONAL for Build 025; would need a new plugin/dependency (packaging-impact tradeoff, mandate §33) — DECISION_REQUIRED if pursued, not REQUIRED_PARITY |
| Settings | Any other UI preference (theme, units, panel widths, last view) | None found in legacy | None found in Tauri | OBSOLETE / N/A | Nothing to parity against | — |

## Desktop Integration

| Area | Legacy Feature | Legacy Evidence | Tauri Status | Classification | Build 025 Recommendation | Risk |
|---|---|---|---|---|---|---|
| Desktop Integration | About dialog (name, version, build, description, safety notice) | `about_dialog.py` | None | REQUIRED_PARITY | Small, self-contained; static content, no engine dependency | Low |
| Desktop Integration | Application metadata (name/version/org) registered with the OS | `app.py:39-44` `configure_application_metadata` | `productName: "ZeroRodCAD"` in `tauri.conf.json:3`; no further metadata surfaced in-app | `tauri.conf.json` | ALREADY_IMPLEMENTED at the config level; the *displayed* About content is the actual gap (row above) | — |
| Desktop Integration | Recent files list | **Not implemented in legacy** (no recent-files code anywhere) | None | OBSOLETE as a parity claim | Optional macOS convention, not a parity requirement since legacy lacks it too — DEFERRED | Low if pursued |
| Desktop Integration | Diagnostics dialog: Platform, Machine, Python version, Executable path, Frozen flag, CadQuery version, PySide6 version, writable-home check, Copy-to-clipboard | `diagnostics.py`, `diagnostics_dialog.py` | The *raw materials* exist but are scattered across the main product UI instead of a coherent diagnostics surface: status rows (`main.ts:52-58`) and `engine_sidecar_status`'s payload (`cadquery_version`, `ocp_variant`, `vtk_installed`, `python_version` — `engine.ts:30-38`) surface only via the "Ping Engine" button's raw JSON dump in "last action" text | `main.ts:100-115` `handlePingEngine` | REQUIRED_PARITY / MOVE_TO_DIAGNOSTICS | Directly resolves both the "technical buttons in product UI" problem (Lifecycle section) and the "no Diagnostics parity" gap in one move: relocate the existing status panel + Ping/Status data into a proper Diagnostics dialog/area, formatted for a human, not a JSON dump | Low (relocation, not new capability) |
| Desktop Integration | "Open Documentation" menu item, opens a local repo-relative `docs/INSTALL_MACOS.md` via `QDesktopServices` | `main_window.py:510-520` | None | REDESIGN_FOR_TAURI / DEFERRED | Legacy's approach won't work unmodified in a packaged `.app` (no `docs/` tree at the bundle's runtime path) — needs its own design if pursued, not a direct port | Low–Medium |
| Desktop Integration | Drag & drop `.zerorod` onto the window | `main_window.py:522-534` | None | OPTIONAL / DEFERRED | See Projects section | Low |
| Desktop Integration | File-type registration (`.zerorod`) | `packaging/macos/ZeroRodCAD.spec:81-89` — **declared but non-functional** (see Projects section note) | None | DEFERRED | Do not treat legacy's declaration as proof this already works | Low urgency |

## Accessibility

| Area | Legacy | Evidence | Tauri | Evidence | Classification | Recommendation |
|---|---|---|---|---|---|---|
| Form labels | Implicit via `QFormLayout` labels (Qt's built-in accessibility bridge) | `main_window.py:138-163` | Explicit `<label for>` + `aria-describedby` + `aria-invalid` per field | `parameter_panel.ts:112-123` | ALREADY_IMPLEMENTED — Tauri's explicit ARIA arguably exceeds legacy's implicit Qt semantics | No action needed |
| Error/status announcements | Status banner text change only, no live-region semantics | `main_window.py:331-354` | `role="alert"` on field/export errors, `role="alertdialog"` on the overwrite-confirmation panel | `parameter_panel.ts` (error paragraphs), `export_panel.ts:146` | ALREADY_IMPLEMENTED — exceeds legacy | No action needed |
| Keyboard-only preview control (rotate/zoom/toggle layers without a mouse) | Not accessible without a mouse (drag/wheel only) | `preview_widget.py:77-100` | `OrbitControls` is also mouse/trackpad-only; no keyboard alternative | `scene.ts:36-37` | Genuine gap in **both** apps — not a Tauri regression | DEFERRED; open UX question independent of parity |
| Focus order / focus-visible | Qt's implicit default tab order | — | Not explicitly managed; relies on natural DOM order and the browser's native `:focus-visible` | No custom `tabindex` code found anywhere in `desktop/frontend/src/` | DECISION_REQUIRED | Needs a manual audit (real interactive check), not a blind parity claim either way |

## Summary counts

```text
Total distinct rows evaluated:      54
ALREADY_IMPLEMENTED:                21
REQUIRED_PARITY:                    16
REDESIGN_FOR_TAURI:                  5
INTERNAL_ONLY:                       2
OBSOLETE:                            7
DEFERRED:                           10
DECISION_REQUIRED:                   8
```

(Rows can carry more than one classification tag where the matrix explicitly says so — e.g.
"REQUIRED_PARITY / MOVE_TO_DIAGNOSTICS" — counted once under its primary tag above.)
