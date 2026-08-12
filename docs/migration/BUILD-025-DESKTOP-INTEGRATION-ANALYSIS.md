# Build 025 — Desktop Integration Analysis

Discovery document, produced before any Build 025 implementation. Covers menus, shortcuts,
preferences, window state, file association, recent files, drag & drop, About, diagnostics, and
accessibility — cross-referencing the Feature Parity Matrix rather than repeating its evidence.

## 1. Menus

Tauri currently defines **no native menu at all** — `lib.rs`'s `tauri::Builder` chain
(`lib.rs:23-56`) has no `.menu(...)` call, and `tauri.conf.json` has no `menu` config. The only
menu bar a user currently sees is whatever the OS/Tauri default provides for a menu-less app.

Legacy's menu bar (`main_window.py:229-245,_build_menu_and_toolbar`):

```text
File               Help
  New                Open Documentation
  Open…              Diagnostics…
  Save               ───────────────
  Save As…           About ZeroRodCAD Desktop
  Export STL / STEP…
  ───────────────
  Quit
```

No Edit, View, or Window menu exists in legacy (confirmed by reading the entirety of
`_build_menu_and_toolbar` — only two `menuBar().addMenu()` calls exist).

**Proposed Build 025 macOS menu structure** (proposal only, not authorized for implementation):

```text
ZeroRodCAD                File              Help
  About ZeroRodCAD          New    ⌘N         Documentation
  Preferences…  ⌘,          Open…  ⌘O         Diagnostics…
  ───────────────           Save   ⌘S         ───────────────
  Quit ZeroRodCAD ⌘Q        Save As… ⇧⌘S      About ZeroRodCAD
                             ───────────────
                             Export Model…
```

Rationale for each deviation from a blind port:

- The **`ZeroRodCAD` app menu** (About/Preferences/Quit) is a macOS convention Qt's `QMenuBar`
  does not model the same way — Tauri v2's native menu API supports it directly, and moving
  About/Quit there is more idiomatic than leaving them in File/Help as legacy does. This is
  `REDESIGN_FOR_TAURI`, not a literal port.
- **No Edit menu** — legacy has none, and the Feature Parity Matrix found no undo/redo or
  clipboard-worthy app-level actions needing one; native text-field Cut/Copy/Paste is free from the
  OS regardless of a custom Edit menu's existence.
- **No View menu proposed by default** — only relevant if Reset View/layer-visibility controls
  (Feature Parity Matrix, Preview section) end up designed as menu items rather than inline preview
  buttons; that is a UI-layout decision for the implementing milestone, flagged `DECISION_REQUIRED`
  in the matrix, not decided here.
- **`Preferences…`** only makes sense if a Settings surface is actually built (see §3) — legacy has
  none, so this is speculative and should be dropped from the menu if Build 025 doesn't end up
  building Settings.
- **Window menu** — Tauri/macOS typically provides a default one once any native menu exists; no
  custom items are needed unless multi-window support is ever added (out of scope, no evidence
  anyone needs it).

## 2. Keyboard shortcuts

Full parity matrix already recorded in `BUILD-025-FEATURE-PARITY-MATRIX.md`'s "Keyboard Shortcuts"
section. Summary: ⌘N/⌘O/⌘S/⇧⌘S are `REQUIRED_PARITY` (blocked on Project Persistence existing at
all — a shortcut with nothing to bind to is meaningless), ⌘Q is `ALREADY_IMPLEMENTED` (native,
already triggers sidecar shutdown), ⌘E and ⌘Z/⇧⌘Z are explicitly **not** required parity because
legacy itself never had them (confirmed by absence, not omission — `main_window.py:88-93`'s
`export_action` has no `setShortcut` call, and no `QUndoStack` exists anywhere in the codebase).
⌘, is speculative, contingent on §3.

## 3. Settings / Preferences

Legacy's *entire* persistent-settings footprint is one `QSettings` key:
`"paths/last_directory"` (`main_window.py:546-550`), shared across Open, Save As, and Export
dialogs. There is no window-geometry persistence (`self.resize(1240, 780)` runs unconditionally
every launch — `main_window.py:57`), no theme, no unit preference, no "last used parameter set"
beyond whatever the last-saved/opened project file itself contains.

Categorized per the mandate's §20 split:

| Item | Category | Evidence | Build 025 status |
|---|---|---|---|
| Last-used directory for file dialogs | Session State / Application Preference | `main_window.py:546-550` | Bundle with Project Persistence (§ above), low effort |
| Window size/position | Application Preference (if pursued at all) | Not persisted even in legacy | `OBSOLETE` as a parity claim; `OPTIONAL` if pursued — needs a new Tauri plugin (`tauri-plugin-window-state` or equivalent), a real packaging-impact question (mandate §33), not free |
| ZeroRod geometry parameters | Project Data | `zerorod-parameters/v1`, unchanged | Already correctly scoped as project data via the export/persistence work — not a "setting" |
| Theme / units / any other UI preference | N/A | None found in either app | Nothing to build — do not invent |

No evidence anywhere supports a broader Settings/Preferences surface than "remembered last
directory." Recommendation: treat this as a small addition folded into Project Persistence, not a
standalone Settings milestone, unless the Diagnostics-area design (§5) or a future decision
surfaces a genuine need for more.

## 4. Window state

Covered by §3's table — neither app persists geometry today. No action required for parity; any
future addition is `OPTIONAL`/`DEFERRED`, not a gap.

## 5. Diagnostics area (design analysis, not implementation)

This is the single highest-leverage Desktop Integration item, because it resolves two separate
findings at once:

1. The Lifecycle Analysis's finding that four technical controls (status panel, Start/Check Engine,
   Ping Engine, Request Preview Data) currently sit inside the main product UI and should be
   `REMOVE_FROM_PRODUCT_UI`/`MOVE_TO_DIAGNOSTICS`.
2. The Feature Parity Matrix's finding that legacy's `DiagnosticsDialog` (Platform, Machine, Python
   version, Executable path, Frozen flag, CadQuery version, PySide6 version, writable-home check,
   Copy-to-clipboard — `diagnostics.py`, `diagnostics_dialog.py`) has no Tauri equivalent.

**A relocated status panel + a version-info dialog together already cover essentially everything
legacy's Diagnostics dialog covers**, with Tauri-appropriate substitutions:

| Legacy diagnostic | Legacy source | Tauri-side equivalent already available | Source |
|---|---|---|---|
| Platform / Machine | `platform.platform()`, `platform.machine()` | Not currently surfaced anywhere in Tauri; trivial Rust `std::env`/`sys_info`-equivalent addition | — |
| Python version | `platform.python_version()` | `SidecarStatus.python_version` | `engine.ts:33`, sourced from `engine_sidecar_status` |
| Executable / Frozen | `sys.executable`, `sys.frozen` | Not currently surfaced; low-value in a Tauri context (the sidecar's onedir executable path is knowable but not currently exposed) | — |
| CadQuery version | `_distribution_version("cadquery")` | `SidecarStatus.cadquery_version` | `engine.ts:34` |
| PySide6 version | `_distribution_version("PySide6")` | N/A — replaced by `SidecarStatus.ocp_variant`/`vtk_installed` (the Tauri-relevant equivalent question is "is this the No-VTK OCP variant," not "what Qt version") | `engine.ts:35-36` |
| Writable home directory | `os_access_writable(Path.home())` | Not currently checked; a reasonable candidate to keep if implemented | — |
| Copy-to-clipboard | `QApplication.clipboard().setText(...)` | Not currently implemented (no clipboard API call found in `desktop/frontend/src/`) | — |
| *(no legacy equivalent)* | — | pid, ping round-trip latency, engine lifecycle state, mesh summary counts (vertices/triangles/lines) | `main.ts:86-131` — genuinely new diagnostics value the sidecar architecture makes possible that Qt/VTK never exposed |

Recommendation: design a single Diagnostics view (dialog or dedicated area, a UI-layout choice for
the implementing milestone) that hosts the relocated status panel plus a version-info summary
sourced from `app_info`/`engine_sidecar_status`, replacing all four now-orphaned buttons and the
raw "last action" log with human-readable presentation — not a JSON dump.

## 6. File association

Feature Parity Matrix already records the key finding: legacy's `Info.plist` declares
`.zerorod` as an `Editor`-role document type (`packaging/macos/ZeroRodCAD.spec:81-89`), but this is
**non-functional** — nothing in `app.py`/`main_window.py` reads `sys.argv` for a file path or
overrides `QFileOpenEvent`. Double-clicking a `.zerorod` file with legacy installed launches the
app but does not open the file. Build 025 should not treat this as "restore existing behavior" —
implementing real file-association support (both the `Info.plist`/`tauri.conf.json` declaration
*and* the actual open-on-launch handling) would be new functionality exceeding legacy, appropriately
classified `DEFERRED` pending a real cost/benefit decision, not silently assumed necessary for
parity.

## 7. Recent files

No evidence of a recent-files list anywhere in legacy (`main_window.py` has no `QSettings`-backed
recent-files array, no "Open Recent" submenu). `OBSOLETE` as a parity claim; genuinely `OPTIONAL`
if pursued as a new macOS-convention nicety, not required by any existing behavior.

## 8. Drag & drop

Legacy accepts a dropped `.zerorod` file onto the main window (`main_window.py:522-534`,
`setAcceptDrops(True)` in `__init__`). Real, working legacy behavior — but low-risk/low-value to
add before Open itself exists (drag & drop is a second entry point to the same `_open_project_path`
logic Open already needs). Recommendation: `OPTIONAL`, sequenced after Project Persistence's Open
action exists, reusing its logic rather than building a parallel path.

## 9. About

Legacy's `AboutDialog` (`about_dialog.py`) shows app name, `"Version {APP_VERSION} · Build
{APP_BUILD}"`, a one-line product description, and a safety notice ("Generated geometry must be
validated in CAD, in the slicer and with a physical prototype before use.") — small, static,
self-contained. No Tauri equivalent exists. `REQUIRED_PARITY`, low effort, no engine dependency —
one of the lowest-risk items in the entire matrix. The safety-notice text in particular should
likely be carried forward verbatim or near-verbatim; it is product-safety language, not
implementation detail.

## 10. Accessibility

Already covered in the Feature Parity Matrix's Accessibility section. Summary: form labeling and
error-announcement semantics are **already ahead of legacy** (`parameter_panel.ts`'s explicit
`<label for>`/`aria-describedby`/`aria-invalid`/`role="alert"` vs. legacy's implicit Qt
accessibility bridge). Two items remain genuinely open in both apps (keyboard-only preview control,
`DEFERRED`) or need a manual audit rather than a code-evidence-only judgment (focus order/
focus-visible, `DECISION_REQUIRED`). No further desktop-integration-specific accessibility gap was
found beyond what the matrix already records — native menu items and dialogs, once built, get
baseline OS accessibility support from Tauri's native menu API "for free," which is itself a reason
to prefer native menus over further custom HTML/ARIA reconstruction for the same actions.

## 11. Security recap

Every item above that requires a new OS-level interaction (file open/save dialogs, About, a
Diagnostics view sourced from existing commands) fits within the existing security discipline:
Rust-mediated, narrowly-scoped, no broad filesystem/shell/process grant to the WebView. No item
identified in this analysis requires a security-boundary change beyond the two narrow dialog
permissions already discussed in the Project Persistence Analysis (`dialog:allow-open` extended to
file-picking, a new `dialog:allow-save`). Native menus themselves require no WebView capability at
all — they are Rust/Tauri-native constructs dispatching to existing or new Tauri commands exactly
like a button click does today.

## 12. Packaging impact

None of the items in this analysis are expected to move the bundle size baseline (~285.9 MiB)
meaningfully — native menus, dialogs, and a diagnostics view are Rust/Tauri/frontend code, not new
Python dependencies, and Tauri's dialog plugin is already linked in (Build 024 M1). Classify overall
packaging impact for this analysis's scope as `small`, pending real measurement once implemented —
per mandate §33, this is a reference estimate, not a guarantee.
