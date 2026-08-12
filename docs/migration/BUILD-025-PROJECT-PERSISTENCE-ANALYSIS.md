# Build 025 — Project Persistence Analysis

Discovery document, produced before any Build 025 implementation. Project persistence is, per the
`BUILD-025-HANDOFF.md`, "genuinely new surface" — unlike export, there is no existing
`export_project`-equivalent sidecar/Rust exposure to reuse; the analysis below establishes what
already exists (the file format), what is genuinely new (the UI/IPC/security surface), and the
canonical-state questions the mandate requires answering before any implementation (§13/§14).

## 1. Existing project file format (already built, engine-side)

`src/zerorodcad/project.py` (35 lines total) already implements a complete, working, versioned
format:

```python
FILE_FORMAT = "ZeroRodCAD Project"
FILE_VERSION = 1

def save_project(path, parameters: ZeroRodParameters) -> Path:
    # forces a `.zerorod` extension, writes:
    {"format": "ZeroRodCAD Project", "version": 1, "parameters": parameters.to_dict()}

def load_project(path) -> ZeroRodParameters:
    # validates format string and version, then ZeroRodParameters.from_dict(payload["parameters"])
```

Key properties:

- **Human-readable JSON**, indented, UTF-8.
- **`parameters.to_dict()`/`from_dict()` is exactly `zerorod-parameters/v1`'s `values` shape**
  (`docs/contracts/ZEROROD-PARAMETERS-V1.md` states this explicitly: "the same shape already used
  by `.zerorod` project files"). This is the single most important fact for Build 025: **the
  project file format and the parameter contract were already designed together** — a project file
  is, structurally, `{"format": ..., "version": 1, "parameters": {<zerorod-parameters/v1 values>}}`.
- **Versioned** (`FILE_VERSION = 1`), with an explicit unsupported-version rejection
  (`ValueError(f"Unsupported project version: ...")`) — no silent fallback.
- **Format-checked**, not just extension-checked (`payload.get("format") != FILE_FORMAT` raises
  `ValueError("Not a ZeroRodCAD project file.")`) — a `.zerorod`-named file with wrong content is
  rejected explicitly.
- Engine-side, framework-independent: `project.py` imports nothing from PySide6 or Tauri — it is
  already shared, reusable logic sitting in `src/zerorodcad/`, the same package the sidecar already
  wraps.

**Conclusion for mandate §12 ("Keine neue Projektarchitektur erfinden, wenn die bestehende
tragfähig ist"):** the existing format is tragfähig (viable) and should be reused unmodified. No
new schema design is needed for the file's on-disk shape.

## 2. What is actually new

Despite the format already existing, three things genuinely do not exist yet and are real Build 025
work:

1. **A sidecar command exposing `save_project`/`load_project`.** Neither function is currently
   reachable from the sidecar's `zerorod-sidecar/v1` command dispatch — only `ping`, `status`,
   `preview`, `parameters_defaults`, `export`, `export_preflight` exist today (`commands.rs:23-249`
   enumerates every Tauri command; none of them touch `project.py`). This is the same
   "expose an existing engine function through a new dedicated command" pattern Build 024 M1 used
   for `export_project` (`docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md`) — not a new engine
   capability, a new *boundary* exposure.
2. **Rust commands + a native save/open dialog capability.** Build 024 added exactly one narrow
   capability, `dialog:allow-open` (folder picker only) — `capabilities/main-capability.json:6`.
   Project Open needs a *file* open dialog (not folder); Project Save/Save As needs a *save* dialog
   — neither capability is granted today. Both are narrow, single-purpose `tauri-plugin-dialog`
   permissions, consistent with the existing security boundary (see §6).
3. **Frontend UI and state**: New/Open/Save/Save As triggers, a `current_path`-equivalent piece of
   state, and the canonical-state/dirty-state semantics this document works out below.

## 3. Legacy's actual New/Open/Save/Save As behavior (evidence, not assumption)

| Action | Legacy behavior | Evidence |
|---|---|---|
| New | Resets `current_path` to `None`, reloads `ZeroRodParameters()` (canonical defaults), triggers a full workspace update | `main_window.py:440-443` |
| Open | Native `QFileDialog.getOpenFileName` filtered to `*.zerorod`; on a chosen path, `load_project()` then `_load_parameters()` then `_update_workspace()` | `main_window.py:445-454,536-545` |
| Save | If `current_path is None`, delegates to Save As; else `save_project(current_path, self._parameters())` | `main_window.py:456-464` |
| Save As | Native `QFileDialog.getSaveFileName`, default filename `f"{project_name}.zerorod"` in the last-used directory; on success, updates `current_path` and remembers the directory | `main_window.py:466-483` |
| Error handling | Both Open and Save wrap the call in try/except, showing `QMessageBox.critical` with the raw exception string on failure | `main_window.py:463-464,482-483,543-544` |
| **Dirty-state tracking** | **None.** No `isWindowModified`, no `closeEvent` override anywhere in `main_window.py` (confirmed by a full-file read) — New/Open silently discard unsaved edits; quitting or closing the window does not warn at all | — (absence confirmed, not assumed) |

The absence of dirty-state tracking is a real gap in legacy itself, not a feature to port. See §5.

## 4. Canonical state: what exactly does "Save" persist?

The mandate (§13) requires this answered with justification, not assumed, given Build 023/024's
existing `draft`/`accepted` semantics must not be broken by persistence.

**Recall the existing semantics** (established Build 023 M4, reused unmodified by Build 024's
export): `accepted` means "the parameter values currently represented in the preview, or the last
state a completed engine round trip (live-preview or Apply-triggered) confirmed."
`draft` is whatever is currently typed, which may be invalid, may still be debouncing, or may not
yet have produced a successful preview.

**Legacy has no draft/accepted distinction at all** — `main_window.py`'s `_parameters()` reads
widget values directly at save time, with no concept of "the last state the preview actually
confirmed" vs. "what's currently typed." Legacy's Save can therefore persist parameter values that
have never successfully built a preview (e.g. mid-edit, or after a validation error the user hasn't
noticed yet — `_update_report_only`'s `except` branch swallows exceptions into an "Input error"
banner without blocking the text fields from further edits).

**Recommendation, with justification:**

- **Save should persist `accepted`, not `draft`** — for the same reason Build 024's export sources
  `accepted` and never `draft` (`docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md`: "canonical
  export-source semantics decided (the frontend's `accepted` state, not the draft)"). This keeps
  a single, consistent rule across the app: **"the model the user is currently looking at" is what
  gets exported and what gets saved** — not a possibly-invalid, possibly-unconfirmed in-progress
  edit. Diverging from this (e.g. saving `draft`) would mean Save and Export disagree about what
  "the current model" means, which the mandate explicitly warns against (§13: "Darf ein ungültiger
  Draft gespeichert werden?" — answered here: **no**).
- **Consequence:** the Save action should be disabled (or should force-resolve the pending draft
  first) under the same conditions Export's trigger is already disabled under — `draft` has
  unresolved errors, or live-preview is still pending/updating (`export_panel.ts:127-132`
  `isTriggerEnabled` is the existing, already-tested precedent to reuse the *logic* of, not the
  code itself, since Save is a different action).
- **What happens to a draft with invalid values when the user tries to Save:** per the above, Save
  is not offered (or the user is prompted to resolve/discard the pending edit) rather than silently
  persisting a value set that has never round-tripped through the engine successfully. This is
  stricter than legacy (which saves whatever is in the widgets, valid or not) — a deliberate
  improvement, not a parity requirement, since legacy's own behavior here is an oversight, not a
  designed feature (no test or documentation anywhere claims it as intentional).
- **What happens during a live-preview update in flight:** Save reads `accepted`, which by
  definition does not change until a request completes — so a Save that fires mid-update simply
  persists the *previous* confirmed state, identical to what Export already does today. No new
  concurrency handling is needed; this reuses Build 023 M4's existing atomicity guarantee for
  `accepted` writes.
- **Is Save equivalent to Apply/Accept?** No — Save is orthogonal to Apply. Apply/live-preview
  updates `accepted` from `draft`; Save persists whatever `accepted` currently holds to disk. A
  user can Save the same `accepted` state repeatedly without any Apply in between (e.g. Save As
  under a new name with no parameter changes).

## 5. Dirty-state semantics

The mandate (§14) asks whether `draft dirty` / `preview dirty` / `project dirty` are all actually
needed, or whether this is overcomplication.

- **`draft dirty`** (`isDraftDirty(draft, accepted)`) **already exists** and is reused unmodified
  (`parameter_state.ts`, established Build 023 M4) — it answers "does the current typed draft
  differ from what's been accepted/previewed yet."
- **`preview dirty`** is not a separate concept — it is already fully expressed by the existing
  `LivePreviewStatus` type (`"up-to-date" | "pending" | "updating" | "error"`,
  `parameter_panel.ts:134`). Introducing a second "preview dirty" flag would duplicate information
  this status already carries. **Recommendation: do not add it** — reuse `LivePreviewStatus`
  directly wherever "is the preview still catching up" needs to be known (e.g. gating Save the same
  way Export is already gated, per §4).
- **`project dirty`** is genuinely new: "has `accepted` (or the project's identity — path/name)
  changed since the last successful Save/Open?" This has no existing equivalent anywhere in
  Build 022–024, since nothing before Build 025 has a concept of "since last saved." This is the
  one new piece of state Build 025 actually needs to introduce: e.g. a stored snapshot of `accepted`
  (or a hash/equality check against it) taken at the moment of the last successful Save or Open,
  compared against the live `accepted` value.

**Conclusion: three distinct dirty concepts are not needed.** `draft dirty` and `LivePreviewStatus`
already exist and already answer two of the mandate's three questions; only `project dirty` is new.
This keeps the state model additive rather than introducing unnecessary complexity (mandate §14's
own "keine unnötige Zustandskomplexität" instruction).

## 6. Security: native dialogs within the existing boundary

Build 024 established the precedent: one narrow, explicitly-justified `tauri-plugin-dialog`
permission per capability, never a broad filesystem grant
(`capabilities/main-capability.json`'s own description: "no filesystem read/write/list capability
of its own; the WebView still cannot read a directory listing or a file's contents directly, only
receive an opaque path string").

Project persistence needs, at minimum:

- **`dialog:allow-open`** already exists but is currently scoped to folder-picking
  (`select_export_directory` calls `.file().pick_folder(...)` — `commands.rs:143-158`). The same
  permission string covers file-open dialogs too (`tauri-plugin-dialog`'s `allow-open` permission
  is not folder-specific at the ACL level) — opening a `.zerorod` file needs a new Rust command
  (e.g. `select_project_file`) calling `.file().add_filter("ZeroRodCAD Project", &["zerorod"]).pick_file(...)`
  instead of `pick_folder`, but may not need a *new* capability grant, only a new command using the
  existing permission. This should be confirmed against the actual `tauri-plugin-dialog` ACL
  schema during implementation, not assumed here.
- **A new `dialog:allow-save`** permission for Save As's native save dialog — genuinely new,
  narrowly scoped exactly like `dialog:allow-open` was in Build 024 M1, with the same
  justification pattern (WebView receives only an opaque chosen path back, never gains filesystem
  read/write/list capability itself).
- **File read/write itself** (actually loading/writing the `.zerorod` JSON) must stay Rust/sidecar
  -owned, exactly like export's actual file writes are sidecar-owned and never WebView-owned. The
  WebView's role is unchanged from Build 024's pattern: hand a user-chosen path to a Rust command;
  Rust forwards it to the sidecar; the sidecar (which already has `project.py`) does the actual
  read/write.

No broad filesystem capability, no `@tauri-apps/plugin-shell`, no WebView-side file API — the
security boundary established in `ADR-022-001` and preserved through Build 024 does not move.

## 7. Error cases

| Case | Legacy behavior | Recommendation |
|---|---|---|
| Open a corrupt/non-JSON file | `json.loads` raises, caught by `main_window.py`'s try/except around `_open_project_path`, shown via `QMessageBox.critical` with the raw exception text | Structured error code (e.g. `project_invalid_json`), formatted user-facing message — consistent with the existing `EngineError`/`isEngineError` pattern export already uses, never a raw Python exception string |
| Open a file with wrong `format` string | `ValueError("Not a ZeroRodCAD project file.")`, same generic critical dialog | Structured `project_invalid_format` code |
| Open a file with an unsupported `version` | `ValueError(f"Unsupported project version: {version}")`, same generic dialog | Structured `project_unsupported_version` code, with the version numbers in `details` (mirrors `zerorod-parameters/v1`'s `details` pattern) |
| Open a file whose `parameters` fail `ZeroRodParameters.from_dict` (unknown field) | Raises `ValueError`, same generic dialog | Same structured-error treatment |
| Save to an unwritable path | Not specifically handled — generic `Exception` catch, `QMessageBox.critical` | Same two-layer verification discipline export already established (`export_result.rs`) is a reasonable precedent to reapply, though project files are a single small write, not a multi-file export — proportionate error handling, not necessarily a second Rust-side structural-validation layer |
| Dialog cancellation (Open/Save As) | Silently returns (`if not filename: return`) | Same "cancellation is normal, never an error" precedent already established for export (`export_panel.ts:207-212`) |

## 8. Tests needed

- Sidecar-level: round-trip save/load through the new command(s) against `project.py` (already has
  its own unit tests presumably — verify during implementation, not assumed here since this
  document is read-only discovery).
- **Real IPC boundary tests** for any new Rust command with a `project_path`/`output_path`-style
  snake_case argument — Build 024 M2's bugfix (`docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md`) is
  the direct precedent: any new command taking an underscored parameter name needs
  `#[tauri::command(rename_all = "snake_case")]` from the start, verified with a real
  `tauri::test::get_ipc_response` dispatch, not a mocked `invoke()` assertion — see
  [[feedback-tauri-command-arg-casing]] for why this bug class recurs.
- Frontend: dirty-state transition tests (draft dirty, live-preview status, and the new project-dirty
  flag) mirroring the existing `parameter_state.test.ts` style.
- Human validation: required — this is a new user-facing workflow with native dialogs and real
  file I/O, the same category of change Build 024 M2's Round 1 Human Validation caught a real defect
  in.

## 9. Open decisions (not resolved here — flagged per mandate §13)

- Exact new sidecar command names/shapes for project save/load (a boundary-exposure design
  decision, not a discovery-phase decision).
- Whether Save As's default filename should reuse legacy's `f"{project_name}.zerorod"` pattern
  (reasonable, low-risk to carry forward — no evidence against it).
- Whether opening a project should overwrite the current in-memory draft outright (matching legacy)
  or prompt if the current project is dirty (an improvement legacy doesn't have, consistent with
  the dirty-state model this document establishes) — a genuine design choice for the implementing
  milestone, not resolvable from evidence alone.
