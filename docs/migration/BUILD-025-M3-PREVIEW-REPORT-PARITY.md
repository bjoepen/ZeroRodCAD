# Build 025 / Milestone 3 — Preview & Report Parity

Engineering record. Closes the remaining model-inspection and report-related feature-parity gaps
between the legacy PySide6 application and the productive Tauri v2 desktop application: Reset
View, Body/Rod/Strings visibility, and an in-app Instrument Report — reusing the existing
architecture (Tauri v2 → Rust → persistent Python sidecar → CadQuery → `zerorod-mesh/v1` →
Three.js) unmodified.

## Baseline

- Build 025 M1 (Project Persistence): `feature/build025-m1-project-persistence`, final commit
  `d3c93b9` — Gate `BUILD-025-M1 CONSISTENCY GATE: PASS`, Human Validation PASS.
- Build 025 M2 (Product UI Productization & Lifecycle Polish): `feature/build025-m2-product-lifecycle`,
  commit `781466d` — Gate `BUILD-025-M2 CONSISTENCY GATE: PASS`. Human Validation **PASS**,
  communicated directly by the Project Owner as this milestone's authorization (see
  `docs/migration/BUILD-025-M2-HUMAN-VALIDATION.md`, §2 of the mandate — recorded as an overall
  PASS, not itemized against each checklist line, since that is the granularity actually reported).
- This milestone: `feature/build025-m3-preview-report-parity`, branched from `781466d`.

## Build identity correction (§3/§43 of the mandate)

M2's own `app_info()` shipped its entire Human Validation artifact still reporting
`milestone: "M1"` — the field was never bumped during the M2 milestone despite `commands.rs`'s own
doc comment instructing exactly that ("update both fields together, here only, at the start of each
new milestone"). Root cause was a **process** miss, not a mechanism defect: the single-source design
was already correct (nothing else hardcodes build/milestone — `diagnostics_panel.ts` is the only
renderer, reading `app_info()` live), but M2's own `validate-build025-m2.sh` gate made the miss
*worse*, not better — it asserted `milestone == "M1"` as a deliberate, rationalized
"STALE_GATE_ASSUMPTION" instead of asserting what an M2 gate should actually require
(`milestone == "M2"`).

Fix: `commands.rs`'s `app_info()` now reports `milestone: "M3"`. The pinning test was renamed from
`app_info_reports_build_025_m1` to `app_info_reports_current_milestone` (a value-pinning test alone
cannot prevent a future forgotten bump — updating the pinned value and forgetting the real bump are
the same mistake), and a new, general-form regression test was added:
`app_info_never_reports_a_stale_earlier_build_025_milestone`, which fails if `milestone` is ever
`"M1"` or `"M2"` again — not just the one specific `024`/`M2` pair the M1 fix already guards.
`scripts/validate-build025-m3.sh` asserts `milestone == "M3"` specifically for this gate, not
"unchanged from before" — the lesson from M2's gate mistake applied directly.

A second, pre-existing, currently-inert milestone string was found and **deliberately not
touched**: `src/zerorod_sidecar/main.py`'s `MILESTONE = "build023-m1"` constant (returned by the
sidecar's own `status` command, `SidecarStatus.milestone` in the frontend's `engine.ts`). It has
been frozen since Build 023 M1 and has zero visible product surface — nothing in the frontend ever
reads or renders `SidecarStatus.milestone` (confirmed by search). Since the mandate's own scope for
this correction is "a narrow metadata correction, not a new versioning system" and this field is
neither the source of the actual bug nor duplicated into any frontend file, it is left as
documented, known, harmless technical debt rather than expanded into out-of-scope sidecar/protocol
changes.

## Research — legacy PySide6 vs. the productive architecture (§5)

Read directly, not inferred from control names:

- **`preview_widget.py`**: `reset_view()` resets `_yaw`/`_pitch`/`_zoom` to three fixed constants
  (`-28.0`, `22.0`, `1.0`) — legacy has exactly **one** view-recovery control, not a separate
  Fit-View/Reset-View pair. `show_body`/`show_rod`/`show_strings` are plain booleans, default
  `True`, filtered in `_visible_meshes()`/`_visible_lines()` by mesh/line name (`"body"`, `"rod"`,
  `"strings"`).
- **`main_window.py`**: wires a "Reset View" `QPushButton` and three `QCheckBox`es (Body/Rod/
  Strings, all checked by default) directly to the widget above; a `QTextBrowser` tab labeled
  "Instrument Report" is repopulated via `self.report.setMarkdown(build_report(parameters))` on
  **every** keystroke (`_schedule_update` → `_update_report_only()`, synchronous, using whatever is
  currently typed — even mid-invalid-input, wrapped in try/except). This is legacy's own naive
  behavior, not a designed feature worth reproducing — the productive app already has an
  accepted/draft distinction legacy lacks entirely, and the mandate's own §18/§21 explicitly direct
  following `accepted`, not raw draft typing.
- **`zerorodcad/report.py`**: `build_report(p: ZeroRodParameters) -> str` — a plain Markdown string
  (headings, two tables, a validation bullet list, a closing notice paragraph). Confirmed to be the
  **same, single, canonical implementation** already used by `zerorodcad.export.save_report()` —
  i.e. already the source of the productive app's exported `report.md` file since Build 024. No
  second implementation existed to discover; the milestone's job is exposing this one function
  through a new sidecar/Rust boundary, mirroring `export`'s own precedent exactly.
- **`zerorodcad/parameters.py`**: `ZeroRodParameters` carries the 16 canonical fields plus roughly a
  dozen `@property`-derived engineering values (`string_count`, `string_entry_angle_deg`,
  `string_diameters_mm`, `string_heights_over_fretboard`, `rod_radius`, `tangent_point_yz`, …) —
  confirming the mandate's §6 concern is real and already correctly centralized: every derived
  value `build_report()` uses is already backend-owned, computed once, not something a frontend
  reimplementation could get subtly wrong.
- **Mesh contract naming**: `zerorodcad/preview.py`'s `build_preview_scene` names its body/rod
  meshes exactly `"body"`/`"rod"` and its string lines `"strings"` — identical to legacy's own
  naming, and already passed through unchanged into every `zerorod-mesh/v1` payload's
  `meshes[].name`/`lines[].name` fields (`mesh.ts`'s `RenderableMesh.name`). Visibility needed no
  mesh-contract change at all — the names it filters by already existed.

## Reset View (§7-9/§30-31)

**Decision: exactly one control, "Reset View"**, per the discovery above (§7's own fallback:
"If discovery shows only one behavior is required for parity, implement the smallest correct
product behavior"). Implementation reuses 100% existing machinery — no second camera algorithm:

- `scene.ts` gains `boundsFromVisibleObjects(root)`, a pure function using
  `Object3D.traverseVisible` (which skips invisible subtrees entirely, unlike
  `Box3.expandByObject`, which ignores `.visible`) so a hidden layer never reserves frame space
  (§12). Returns `null` when nothing visible has geometry — callers treat that as a safe no-op.
- `preview.ts`'s new `resetView()` is three lines: compute bounds from the *currently visible*
  scene contents, then call the **existing** `fitCameraToBounds` (unchanged since Build 022 M3) —
  the same fixed-relative-angle algorithm every other refit in the app already uses. No backend
  call, no geometry regeneration, no OrbitControls/renderer recreation, no project-dirty effect
  (§9) — structurally guaranteed by what the function touches (camera/controls only), not merely
  asserted.

## Body/Rod/Strings visibility (§10-15/§32)

`preview.ts` gains a `ModelLayer` type (`"body" | "rod" | "strings"`, matching the mesh contract's
existing names verbatim) and a pure `applyModelLayerVisibility(group, visibility)` function, plus
closure state (`layerVisibility`, default `{body: true, rod: true, strings: true}` — §14) that
persists independently of any single `commitPreview` call's Object3D instances. This durability is
the actual mechanism behind §13's named regression case: `commitPreview`'s `clearGroup` +
recreate cycle destroys and rebuilds Mesh/LineSegments objects on every geometry refresh, so
visibility state cannot live on those objects — `commitPreview` now calls
`applyModelLayerVisibility` immediately after creating them, re-applying whatever was last set for
each layer before the frame is ever rendered.

`view_controls.ts` (new) is the compact model-view tool area (§25): three checkboxes plus the Reset
View button, wired through a small `ViewControlsIO` interface whose only capabilities are
`resetView`/`setLayerVisible`/`isLayerVisible` — it is structurally incapable of calling the
backend, touching `accepted`, or dirtying the project, since nothing in its interface exposes any
of those. Plain product labels ("Body", "Rod", "Strings", "Reset View" — §15), explicit
`<label for>` associations, native checkboxes (inherently keyboard-operable, state
programmatically available via `.checked`, no color-only indication).

## Instrument Report (§16-23/§33)

**Backend**: one new, additive sidecar command, `report` (`src/zerorod_sidecar/main.py`'s
`_run_report_command`), request-shaped exactly like `preview` (`parameters` is the
zerorod-parameters/v1 object directly — no `output_directory`-style wrapper, a report has nowhere
to write). Same Level 1-3 validation as `preview` (`parse_parameters_request` +
`validate_parameters`); on success, returns `{"markdown": build_report(params)}` — `build_report`
called unmodified, no CadQuery geometry construction (proven directly:
`test_report_does_not_construct_cadquery_geometry` monkey-patches `build_preview_scene` to raise if
ever called from this path). `zerorod-sidecar/v1`'s envelope is unchanged — this is a new command
name, not a version bump (§19/§33), documented in
`docs/contracts/ZEROROD-PARAMETERS-V1.md`'s new `report` command section.

A new Rust command, `engine_report` (`commands.rs`), forwards `parameters` verbatim (identical
shape to the existing `engine_preview_mesh_with_parameters`) and structurally validates the result
(`validate_report_result` — a non-empty `markdown` string must be present, mirroring
`mesh::validate_and_summarize`'s "never trust a raw sidecar payload" discipline, scaled down to the
one field this result actually has) before it can ever reach the WebView as a success.

**Frontend**: `report.ts` holds `requestReport()` (the IPC call, identical request-building pattern
to `requestPreviewMeshWithParameters`) and a small, hand-rolled renderer,
`renderReportMarkdownToHtml()`, for the *specific*, *fixed* Markdown subset `build_report()` actually
emits (H1/H2 headings, one table per section, a bullet list, plain paragraphs) — deliberately not a
general Markdown parser or a new dependency (§35: "do not add a charting/report framework just to
display report values"). Tested directly against a real, verbatim-captured `build_report()` output
sample, not a hand-simplified approximation.

`report_panel.ts` sources report content from `io.getAccepted()` only — the same "what the user
sees is what the report describes" rule §18 restates from export's own precedent; there is no path
in this module to a draft value at all. It fetches on open and via `refreshIfVisible()` (wired into
the same `onChange` hook `export_panel.ts`/`project_panel.ts` already use), which is a no-op unless
the panel is open **and** `accepted` actually changed (`parameter_state.ts`'s existing `valuesEqual`
— a genuine deep-equality check, not reference equality, so a Reset-then-edit-back-to-original
sequence doesn't trigger a spurious refetch), directly satisfying §21's "avoid firing expensive
duplicate backend requests on every keystroke" even though the hook itself fires on every
live-preview status transition. A fetch failure only ever sets this panel's own local presentation
state — no path to preview, `accepted`, or project-dirty state exists for it to touch (§22),
verified structurally (the module imports nothing from `preview.ts`/`parameter_panel.ts`/
`project_state.ts`) as well as by test.

**Report/export consistency (§23)**: since both paths call the literal same `build_report()`
function, they are guaranteed identical by construction — verified directly, not just argued, by
`test_report_command_and_exported_report_md_agree_for_the_same_accepted_state`, parametrized over
the three mandated scenarios (default, `body_width=60`, a changed string-gauge configuration),
asserting the `report` command's `markdown` result is byte-for-byte identical to the `report.md`
file `export` writes for the same accepted values.

## Product UI integration (§25/§26)

`main.ts`'s DOM shell gains one new `.viewport-column` (view controls + report panel above the
unmoved `.viewport`, both `flex: 0 0 auto` so the viewport keeps the available space) — the
sidebar and parameters column are untouched. Neither M3 control lives in
`diagnostics_panel.ts` (unchanged this milestone) — Body/Rod/Strings/Reset View/Instrument Report
are normal product functionality, kept conceptually and physically separate from Diagnostics's
technical information (§26).

## Scope discipline

`engine.rs`, `protocol.rs`, `mesh.rs`, and `export_result.rs` (the lifecycle/protocol/mesh-contract
layer) are unchanged — confirmed via `git diff --quiet` in the validation gate. `zerorodcad/` (the
domain package: parameters/geometry/report/export logic itself) is unchanged — no engineering math
was reimplemented anywhere, satisfying §6. `project_panel.ts`/`project_state.ts` (M1),
`parameter_panel.ts`/`startup.ts` (M2's automatic-initial-preview/startup coordinator),
`live_preview.ts`, `export.ts`/`export_panel.ts` (Build 024), and the WebView capability list are
all unchanged. No new dependency was added to `Cargo.toml` or `package.json`. No Build 025 M4 work
(native menus, the Cmd+Q guard-bypass fix, shortcuts, About) was started.

## Known Quit/⌘Q limitation — unchanged, not addressed here (§29 of the mandate)

Carried forward unchanged from Build 025 M1/M2: the default macOS Quit/⌘Q menu item still bypasses
the unsaved-changes guard (see `docs/migration/BUILD-025-M1-NATIVE-CLOSE-BUGFIX.md`). This
milestone builds no native menu infrastructure and does not touch this behavior. Tracked in
`docs/migration/BUILD-025-M3-HUMAN-VALIDATION.md` and reserved for **Build 025 M4**.

## Tests

- `scene.test.ts`: `boundsFromVisibleObjects` — all-visible, a hidden layer excluded entirely, all
  hidden returns `null` (safe no-op), an empty group, and a hidden *parent* group's children
  correctly excluded too.
- `preview.test.ts`: `applyModelLayerVisibility` — independent per-layer toggling, and the exact
  §13 regression case (visibility persists across a simulated `clearGroup`-then-recreate cycle).
  `createPreviewController` itself remains untested directly (constructs a real
  `THREE.WebGLRenderer`, no GPU context under jsdom — the established, pre-existing precedent this
  milestone follows rather than works around).
- `view_controls.test.ts` (new): default-checked state, reflecting a non-default IO state at
  construction, independent per-checkbox toggling, Reset View calling only `resetView()`, plain
  product labels, explicit label association, `dispose()`.
- `report.test.ts` (new): `requestReport`'s exact IPC shape; `renderReportMarkdownToHtml` against
  the real captured default-model Markdown (headings, both tables, the validation list, the closing
  paragraph, no leftover raw Markdown syntax) plus edge cases (HTML escaping, an error/warning
  list, empty input, unrecognized content degrading to a paragraph rather than throwing).
- `report_panel.test.ts` (new): no fetch before open, fetch-on-open using `getAccepted()`, a
  friendly error with Retry on failure, Retry recovering, a friendly local error when there is no
  accepted model yet, collapse-without-refetch, `refreshIfVisible()`'s no-op-while-closed and
  no-op-when-unchanged behavior, and its actual-refetch-on-real-change behavior.
- Rust: `validate_report_result` (accepts well-formed, rejects missing/non-string/empty
  `markdown`), plus a new `report_args_binding_twin` IPC-boundary dispatch test proving
  `report.ts`'s real payload shape is accepted through Tauri's actual generated deserializer, not
  only a mocked `invoke()`.
- Python: 10 new `report` command tests (canonical defaults, byte-for-byte match against
  `build_report()` directly, alternate geometry, a changed string-gauge configuration, domain/schema
  rejection, no traceback, no CadQuery geometry construction, a valid→invalid→valid sequence) plus
  the parametrized report/export consistency test above.
- Full frontend suite: 331 passed, 1 skipped (0 new skips) after this milestone's additions.
  Full Python suite: 380 passed, 1 pre-existing skip (unrelated to this milestone).

## Gate

`scripts/validate-build025-m3.sh` re-verifies the still-valid subset of Build 025 M1/M2's own
checks directly (with explicit `EXPECTED_AUTHORIZED_DRIFT` documentation for `scene.ts`/
`preview.ts`, which the mandate itself directs extending — see the gate script's own comment) plus
this milestone's new checks, then rebuilds the productive sidecar and a fresh release `.app` end to
end, including a real persistent-sidecar smoke sequence exercising `parameters_defaults` → `preview`
→ `report` (twice, default and alternate geometry) → `export` → `shutdown` on the same process. See
the milestone's Abschlussbericht for the actual recorded run result.
