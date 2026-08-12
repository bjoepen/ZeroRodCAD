# Build 025 / Milestone 1 — Project Persistence

Engineering record. Establishes New/Open/Save/Save As against the existing `.zerorod` project
format, a project session model with dirty tracking, and a data-loss-preventing unsaved-changes
guard for New/Open/Quit — the first genuinely new IPC/UI/security surface Build 025 adds (unlike
Build 024's export, which only exposed an already-built engine function through a new boundary).

## Baseline

- Discovery: `research/build025-feature-parity-discovery`, commit `c171ac3` — Gate
  `BUILD-025 DISCOVERY GATE: PASS`.
- Build 024: `feature/build024-m4-integration-completion`, commit `7af13cc` — Gate
  `BUILD-024 CONSISTENCY GATE: PASS`.
- This milestone: `feature/build025-m1-project-persistence`, branched from `c171ac3`.

## Analysis (§7 of the mandate) — verified against source, not assumed from Discovery

1. **How `project.py` loads/saves** (`src/zerorodcad/project.py`, 35 lines, read directly):
   `save_project(path, parameters)` forces a `.zerorod` suffix, writes
   `{"format": "ZeroRodCAD Project", "version": 1, "parameters": parameters.to_dict()}` as indented
   JSON. `load_project(path)` reads and validates `format`/`version`, then
   `ZeroRodParameters.from_dict(payload["parameters"])`. Both raise plain `ValueError`/`OSError`
   subclasses — no structured error codes of its own (that translation is this milestone's sidecar
   boundary's job, mirroring `export`'s own pattern).
2. **What the `.zerorod` format contains**: `ZeroRodParameters.to_dict()` — exactly the same 16
   fields as `zerorod-parameters/v1`'s `values` (confirmed identical field-for-field against
   `src/zerorodcad/parameters.py`; the parameter contract doc already states this explicitly). No
   format migration was needed for full 16-field fidelity (§33) — proven directly by
   `test_project_save_then_open_roundtrips_all_16_fields_for_an_alternate_project`.
3. **How `accepted` is represented in the frontend**: a private closure variable inside
   `parameter_panel.ts`'s `createParameterPanelController` — only reachable via
   `getAccepted()`/`getAcceptedRequest()`. There was no way to *set* it from outside before this
   milestone (only `load()`, always from canonical defaults). `loadProjectValues()` (new) is the
   first external entry point that replaces it with an explicit value set.
4. **Project name / filename semantics**: `project_name` is a `ZeroRodParameters` field (metadata,
   not geometry-affecting), stored *inside* the same JSON as everything else — there is no separate
   "project title" concept. Save As's default filename is derived from it
   (`project_state.ts`'s `defaultSaveFileName`, mirroring legacy's
   `f"{project_name}.zerorod"` — `main_window.py:466-483`), but `project_name` and the on-disk
   filename are never forced to match after that (§28: Open/Save As never rewrite `project_name`
   from a filename, or vice versa).
5. **Existing dialog capabilities**: Build 024 M1 added `dialog:allow-open`, scoped only to
   `select_export_directory`'s `pick_folder()` call. Confirmed directly against the vendored
   `tauri-plugin-dialog` 2.7.2 crate (`~/.cargo/registry/.../tauri-plugin-dialog-2.7.2/permissions/`):
   the ACL gates the whole `open` command (covering `pick_file`/`pick_files`/`pick_folder`/
   `pick_folders` alike, not file-vs-folder separately) and a separate `save` command
   (`allow-save`). So opening a project file reuses `dialog:allow-open` unchanged; only Save As
   needed a new `dialog:allow-save` grant.
6. **Tauri command naming/binding convention**: every existing command with an underscored
   argument name uses `#[tauri::command(rename_all = "snake_case")]` (`engine_export`,
   `engine_export_preflight`) after Build 024 M2's real Human-Validation-caught defect
   (`BUILD-024-M2-EXPORT-BUGFIX.md`). All four new commands with arguments
   (`select_project_save_file`, `engine_project_open`, `engine_project_save`) follow this
   unconditionally from the start, each backed by a real `tauri::test::get_ipc_response` dispatch
   test (see "Tests" below) — not assumed safe by inspection alone.

## Canonical save state (§5/§6)

**Save persists `accepted`, never `draft`** — the same rule Build 024 M1 established for export
("Export what is actually visible"), restated here as "Save what is actually accepted by the
model." Consequence: the Save/Save As triggers are disabled under the same condition Export's
trigger already is (`parameter_panel.ts`'s `LivePreviewStatus` is `"pending"` or `"updating"`, or
nothing has been accepted yet) — `project_panel.ts`'s `isSaveEnabled()` mirrors
`export_panel.ts`'s `isTriggerEnabled()` logic (reused as a pattern, not shared code, since the two
panels are deliberately isolated). This directly answers §23 ("Save bei uncommitted Draft"): Save is
**blocked** until `accepted` is current, rather than waiting asynchronously for a pending Apply to
resolve — the simpler of the two mandate-offered options, and the one with an established,
human-validated precedent (Export) already in this codebase.

An invalid or not-yet-accepted draft can therefore never be saved, by construction — verified
directly in `parameter_panel.test.ts`'s `hasUncommittedDraft` tests and `project_panel.test.ts`'s
Save-enablement tests.

## Project session model (§8) and project-dirty (§9)

`project_state.ts` adds exactly one new piece of state on top of what Build 022–024 already have:

```text
ProjectSessionState { currentPath: string | null; savedBaseline: ZeroRodParametersValues | null }
```

`project_dirty = accepted_current_state != last_saved_state` (§9, verbatim) — deliberately **not**
`draft != saved`. A brand-new project's `savedBaseline` is set to the canonical defaults at New
time (`withNewProjectBaseline`), so a freshly-created or freshly-opened project reads as clean
until an edit is actually *accepted*, not merely typed. This was a deliberate design choice,
verified in `project_state.test.ts`.

Per §14, only one of the mandate's three suggested dirty concepts is genuinely new:

- **`draft dirty`** already exists (`parameter_state.ts`'s `isDraftDirty`) — reused unmodified.
- **`preview dirty`** is not a separate concept; `LivePreviewStatus` (`"pending"`/`"updating"`)
  already expresses "is the preview still catching up," reused directly by `isSaveEnabled()`.
- **`project dirty`** (above) is the one new concept this milestone adds.

## §22 — uncommitted draft, kept separate from project-dirty

Per the mandate's explicit instruction, `project_dirty` is **not** redefined to also cover a
merely-typed draft. Instead, `parameter_panel.ts` exposes a new, separate
`hasUncommittedDraft(): boolean` (`draft` differs from `accepted`, valid or not — mirrors
`isDraftDirty`'s own "including an invalid in-progress edit" semantics), and
`project_state.ts`'s `shouldGuardAgainstDataLoss(session, accepted, hasUncommittedDraft)` combines
the two with a boolean OR at the call site (`project_panel.ts`), never merging them into one flag.

This directly covers the mandate's own worked example: `saved=38, draft="abc" (invalid),
accepted=38` → `project_dirty` is `false`, but `hasUncommittedDraft()` is `true`, so the guard still
fires on New/Open/Quit. Verified directly in `project_state.test.ts`
("is true when an uncommitted draft alone exists, even though project_dirty is false").

**Product rule realized**: Save can never literally rescue an invalid or not-yet-accepted draft
(Save only ever persists `accepted` — see above), so the guard's real protection for this case is
the dialog itself forcing an explicit choice (typically Discard, or Cancel to go fix the input
manually) rather than a silent loss — the "no silent disappearance" requirement is met by the
warning surfacing at all, not by Save somehow capturing unparseable text.

## New / Open / Save / Save As

- **New** (`project_panel.ts`'s `performNew`): fetches canonical defaults through the real
  `parameters_defaults` path, calls `parameter_panel.ts`'s new `loadProjectValues()` (rebuilds the
  form/draft/accepted state **and** drives one real preview fetch+commit so the visible model
  matches immediately — §10), clears `currentPath`, and sets the saved baseline to the just-loaded
  defaults.
- **Open** (`performOpen`): native file dialog (`select_project_open_file`, filtered to
  `.zerorod`) → `engine_project_open` (Rust) → sidecar `project_open` → `zerorodcad.project.
  load_project` (unmodified) → domain re-validation (`validate_parameters`, defense in depth — see
  "Atomicity" below) → only *then* `loadProjectValues()` is called and the session updated. A
  failure at any step before that point leaves the current project, draft, accepted state, and
  preview completely untouched (§12) — verified directly in
  `project_panel.test.ts`'s "leaves the current project/session untouched on a failed open".
- **Save**: if `currentPath` is set, writes directly, no dialog; otherwise behaves exactly like
  Save As (§14).
- **Save As**: native save dialog (`select_project_save_file`, pre-filled with
  `defaultSaveFileName(project_name)`, filtered to `.zerorod`) → `engine_project_save` → sidecar
  `project_save` → `zerorodcad.project.save_project` (unmodified). Cancelling either dialog is a
  normal, non-error outcome — no state changes (§15/§27, mirrors export's own cancellation
  convention).

## Unsaved-changes guard (§17/§18/§21)

`project_panel.ts`'s `guardThenRun`/`confirmQuit` show a single dialog (`role="alertdialog"`,
`Save`/`Discard`/`Cancel`) whenever `shouldGuardAgainstDataLoss` is true, for New, Open, **and**
Quit alike — legacy's silent-discard behavior (confirmed absent in Discovery) is deliberately not
reproduced (§21).

- **Save** inside the guard: if no current path exists yet, opens Save As *inline*; if that
  sub-dialog is cancelled, the **original** New/Open/Quit action is cancelled entirely, not just the
  save (§18) — verified directly (`"§18: cancelling the Save-As sub-dialog cancels the ORIGINAL
  action"`). A failed Save keeps the guard open with an inline error, never silently proceeding.
- **Discard**: proceeds with the original action, dropping the unsaved changes.
- **Cancel**: aborts the original action entirely; nothing changes.

## Quit / window-close (§19/§20)

Investigated directly: `@tauri-apps/api/window`'s `getCurrentWindow().onCloseRequested(handler)`
lets an async handler decide whether the close proceeds — calling `event.preventDefault()` cancels
it; *not* calling it lets Tauri's own close continue normally (confirmed against the package's own
`.d.ts` documentation example, version 2.11.1). ZeroRodCAD has exactly one window and no menu bar
yet (native menus are Build 025 M4's scope) — **window-close and app-quit are treated as
equivalent for this build**, a deliberate, documented choice (not an assumption) recorded in
`main.ts`'s `onCloseRequested` handler comment. This is the single interception point:
`projectPanel.confirmQuit()` runs the same guard as New/Open and resolves `true`/`false`; a `false`
calls `preventDefault()`. Nothing here touches `engine.rs`'s existing `RunEvent::ExitRequested` →
`kill_if_running` shutdown path (verified unchanged — `git diff --quiet -- desktop/src-tauri/src/
engine.rs`, also asserted by the validation gate) — a `true` result simply lets Tauri's normal close
continue into it, neither duplicating nor bypassing Build 022's shutdown logic.

## Atomicity (§12/§29)

**Open** is atomic up to and including domain validation: `project_open`'s sidecar handler
re-validates the loaded parameters with the same `zerorodcad.validation.validate_parameters` used
by `preview`/`export` (defense in depth — a `.zerorod` file did not necessarily come from this
app's own Save) *before* returning, so a domain-invalid or corrupt/malformed file fails with a
structured error and the frontend never calls `loadProjectValues` at all. A rarer Level-4 failure
(the values pass validation but the CadQuery geometry build itself fails) is treated the same as
any other `geometry_error` elsewhere in the app: the project's parameter values are still committed
(they *are* valid), only the preview rendering itself surfaces an error — this is not a violation of
§12's atomicity, which is specifically about the project *file's* validity, not the renderer.

**On-disk write atomicity**: `save_project` (`project.py`, reused unmodified) writes via a direct
`Path.write_text()` call, not a temp-file-then-replace sequence. Per §29's explicit
"keine Scope-Eskalation" instruction, this was evaluated and **not changed**: `export_project`'s own
STL/STEP/report writes are equally non-atomic, and Build 024 M3 already investigated and
deliberately left a related TOCTOU race unmitigated for the same "matches the product's existing
accepted-behavior baseline" reasoning. **Known limitation, explicitly documented, not silently
accepted**: a process crash or forced kill mid-write could leave a truncated `.zerorod` file. No
evidence found that this is more likely or more severe than the equivalent risk already accepted for
export.

## Error model (§27)

`project_open`/`project_save` (sidecar) map to exactly the codes the actual `project.py`/IO
exception structure reliably supports — no invented distinctions:

| Code | When |
|---|---|
| `project_not_found` | Open: path does not exist |
| `project_permission_denied` | `PermissionError` on read or write |
| `project_read_failed` | other `OSError` on read |
| `project_write_failed` | other `OSError` on write |
| `project_invalid` | malformed JSON, wrong `format` string, missing/wrong-shaped `parameters`, unknown parameter field |
| `project_version_unsupported` | `version` != 1 |
| `invalid_parameters_domain` / `invalid_parameter_type` | reused unmodified from the existing parameter contract (Level 2/3) |

Every code is exercised by a direct sidecar-level test (`tests/test_zerorod_sidecar_main.py`). The
frontend (`project_panel.ts`'s `formatProjectError`) maps every one of these to a plain-language
message — never a raw code, never a raw exception/traceback, mirroring `export_panel.ts`'s
`formatExportError`.

## Security (§24)

```text
WebView shell:               NO (unchanged)
WebView filesystem:          NO (unchanged) — only an opaque chosen path crosses the boundary
WebView process:              NO (unchanged)
dialog capabilities:          dialog:allow-open (reused, now also covers file-picking) +
                               dialog:allow-save (new)
project file access ownership: Rust hands the path to the sidecar; project.py (unmodified) is the
                               only thing that ever reads/writes it
IPC:                          unchanged zerorod-sidecar/v1 envelope, no protocol version bump
CSP:                          unchanged
```

No protocol version bump was needed or made (§26) — `project_open`/`project_save` are ordinary new
commands inside the existing `zerorod-sidecar/v1` envelope, exactly like `export`/`export_preflight`
before them.

## UI scope (§34/§35)

Exactly New/Open/Save/Save As, a project name/dirty indicator, the unsaved-changes guard, and
project-related errors — no native menus, no shortcuts, no Diagnostics redesign, no preview
visibility toggles, no Settings, no About, no file association, no Recent Files, no Drag & Drop (all
explicitly deferred to their respective later milestones per the mandate). `project_panel.ts`'s
module doc comment records this UI as a **temporary, compact product path** — Build 025 M4's native
menus will eventually dispatch into the same `ProjectPanelController` this milestone built, not
replace it wholesale.

## Tests (§38)

- **Python**: `tests/test_zerorod_sidecar_main.py` — 24 new tests (roundtrip fidelity for all 16
  fields, every error code above, JSON-serializable/no-traceback, a real geometry proof via the
  actual preview pipeline). `tests/test_zerorod_sidecar_persistent.py` — one new real-subprocess
  test proving the full save → preview → open → open(alt) → export → preview sequence against the
  actual TE-001.1-patched, VTK-free interpreter in a single persistent process (no restart, no
  protocol corruption).
- **Rust**: `commands.rs` — 8 new IPC-argument-binding tests (real `tauri::test::get_ipc_response`
  dispatch, the Build 024 M2 lesson applied proactively rather than reactively).
- **Frontend**: `project.test.ts` (invoke() wrapper shapes), `project_state.test.ts` (dirty
  semantics, the §22 scenario verbatim), `project_panel.test.ts` (24 tests: New/Open/Save/Save As,
  cancellation at every dialog, the full guard flow for New/Open/Quit including the §18 sub-dialog
  cancellation case, atomicity on a failed Open, Save-blocked-while-preview-pending), and 11 new
  `parameter_panel.test.ts` tests for `hasUncommittedDraft`/`loadProjectValues` (including that
  Reset still targets canonical defaults, not an opened project — §28).
- **Real pipeline**: see the real-subprocess test above, plus the packaging-stage bundled-sidecar
  smoke test in `scripts/validate-build025-m1.sh` (preview → project_save → project_open → shutdown
  through the actual PyInstaller onedir binary).

## Known limitations

- `.zerorod` writes are not crash-atomic (see "Atomicity" above) — a documented, not silently
  accepted, limitation consistent with export's existing behavior.
- No project-level Recent Files, file association, or drag & drop yet — all explicitly deferred
  per the Discovery Gap Report, not overlooked.
- The Reset-to-Defaults target for an opened project is always the canonical engine defaults, never
  the opened project's own values — a deliberate, tested choice (§28), not a gap.
