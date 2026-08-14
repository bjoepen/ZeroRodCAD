# Build 025 / Milestone 5 — Repository Cleanup

## Scope

M5 is the final Build 025 milestone: integration, completion, and a controlled repository cleanup
pass. It introduces no new product feature. This document records the cleanup portion; the
milestone's full integration record is [`BUILD-025-COMPLETION.md`](BUILD-025-COMPLETION.md).

The mandate's own rule governed this pass throughout: *"Do not delete something merely because it
looks old. Deletion requires evidence."* Every candidate below was classified before any action was
taken, and only `SAFE_TO_REMOVE` items were eligible for removal.

## Method

A systematic discovery pass was run directly against the repository (`git grep`, `git ls-files`,
and manual cross-reference checks — not a generic linter added for this milestone):

1. Grep inventory across all tracked source for `TODO`, `FIXME`, `HACK`, `TEMP`/`temporary`,
   `deprecated`, `obsolete`, `superseded`, `legacy`, `unused`, `debug`, and stale milestone-name
   markers (`Build 022`..`Build 025 M3`, `Start Engine`, `Ping Engine`, etc.), excluding
   `node_modules/` and `target/`.
2. Dead-frontend-code check: every Rust `#[tauri::command]` registered in
   `desktop/src-tauri/src/lib.rs`'s `invoke_handler` cross-referenced against actual
   `invoke(...)`/`invoke<T>(...)` call sites in `desktop/frontend/src/*.ts` (non-test).
3. Dead-Rust-code check: same registration list cross-referenced against `generate_handler!`.
4. Dead-Python-code check: the sidecar's command dispatch table
   (`src/zerorod_sidecar/main.py`) cross-referenced 1:1 against its handler functions.
5. Validation-script inventory: every `scripts/validate-build*.sh` (33 files, Build 019.1a through
   025) checked for whether it's still a coherent, distinct historical/current gate.
6. Build/packaging-script inventory: every script in `scripts/` and `packaging/` checked against
   which productive pipeline (Tauri onedir sidecar vs. legacy PySide6 `.app`) it belongs to.
7. Duplicate/stale-filename search (`*_old`, `*_new`, `*_backup`, `*_copy`, `*_legacy`, `*_tmp`,
   `*_test2`) plus two specific root-level files noticed during Build 025 M1-M4 work
   (`requirements-dev-build0191a.txt`, `requirements-dev-build0192.txt`).
8. `git ls-files` (not `find`) repo-wide for accidentally tracked `target/`, `node_modules/`,
   `dist/`, `build/`, `.DS_Store`, `__pycache__/`, `*.pyc`.
9. Documentation-staleness check: `README.md`, `ROADMAP.md`, `docs/migration/README.md` for
   current-state claims that had gone stale as M1-M4 completed.

## Protected Areas

Not touched, per the mandate: `experiments/`, `tools/poc/` (TE-001/TE-002 research evidence),
`src/zerorodcad_desktop/` (legacy PySide6 app), accepted ADRs, all Build completion documents and
human-validation evidence, `.git/`.

## Findings

### 1. Stale-marker grep inventory

- `TODO`/`FIXME`/`HACK`: **0 hits** anywhere in tracked source.
- `deprecated`/`obsolete`/`superseded`/`unused` in `.py`/`.ts`/`.rs`: 5 hits, all `KEEP_ACTIVE` —
  either WHY-comments describing legitimate stale-response-discarding behavior
  (`desktop/frontend/src/live_preview.ts:22,69`, `desktop/frontend/src/main.ts:34,92`), or
  `tools/trace_runtime_imports.py`, a deliberate, self-documenting Build-021 compatibility shim
  still referenced by `tests/test_runtime_trace_architecture.py` and four docs —
  `KEEP_ACTIVE`.
- `legacy` in code: all references are correct descriptions of the retained PySide6 reference app
  (parity comments in `preview.ts`/`view_controls.ts`/`main.py`) or `tools/bundle_analyzer/scanner.py`'s
  intentional compatibility-wrapper docstring — `KEEP_ACTIVE`.
- `temp`/`temporary`: all hits are legitimate `tempfile.TemporaryDirectory`/atomic-write-via-temp-file
  patterns or accurately-named test cases — `KEEP_ACTIVE`.
- No stale `Build 022`/`023`/`024`/`025 M1`/`025 M2`/`025 M3` markers found outside historical
  per-milestone docs (which correctly retain their own history) and this milestone's own
  synchronization work (§9 below).

### 2-3. Dead frontend / Rust code

**None found.** All 18 registered Tauri commands (`app_info`, `engine_status`, `engine_ping`,
`engine_sidecar_status`, `engine_preview`, `engine_preview_mesh`,
`engine_preview_mesh_with_parameters`, `engine_report`, `engine_parameters_defaults`,
`engine_export`, `engine_export_preflight`, `select_export_directory`,
`select_project_open_file`, `select_project_save_file`, `engine_project_open`,
`engine_project_save`, `engine_shutdown`, `set_view_menu_checked`) are invoked from productive
frontend source, verified by direct cross-reference. `menu::build_menu`/`handle_menu_event` are
called directly from Rust menu-setup code, not IPC, as expected — `KEEP_ACTIVE`.

### 4. Dead Python/sidecar code

**No safe Python cleanup identified.** `src/zerorod_sidecar/main.py`'s command dispatch table
(`ping`, `status`, `preview`, `report`, `export`, `export_preflight`, `parameters_defaults`,
`project_open`, `project_save`, `shutdown`) maps 1:1 onto its `_run_*_command` handlers — no
orphaned branch, no orphaned handler.

### 5. Validation scripts

All 33 `scripts/validate-build*.sh` scripts form a coherent, complete historical gate sequence
(Build 019.1a through the new Build 025 master gate) — `KEEP_HISTORICAL_EVIDENCE` for superseded
per-milestone gates of completed builds, `KEEP_ACTIVE` for Build 025's own M1-M4 gates and the new
`validate-build025.sh` master gate. None were abandoned/broken one-off duplicates; none removed,
consistent with §24 of the mandate ("do not delete milestone validation scripts just because a
master gate exists").

### 6. Build/packaging scripts

One authoritative productive path confirmed: `scripts/build-productive-desktop-app.sh` →
`packaging/tauri/sidecar-onedir.spec` (Tauri onedir sidecar, `cadquery-ocp-novtk`, referenced by
28 files including README/ROADMAP/every Build 022-025 completion doc). A second script family
(`scripts/build_macos_app.sh`, `package_macos_release.sh`, `analyze_pyinstaller_build.sh`,
`report_macos_bundle.sh`, `verify_macos_app.sh`, `create_macos_icon.sh`,
`create_packaging_venv.sh`, `audit_dependencies.sh`, `report_suspect_dependencies.sh`) all target
`dist/ZeroRodCAD Desktop.app` — the **legacy PySide6 app's** own packaging/analysis tooling, not a
competing productive Tauri pipeline. Classification: `KEEP_LEGACY_REFERENCE` — these support the
explicitly-retained legacy reference app and are out of scope to remove under the mandate's PySide6
policy (§5).

### 7. Duplicate/stale files

No `*_old`/`*_new`/`*_backup`/`*_copy`/`*_legacy`/`*_tmp`/`*_test2` files found anywhere in the
tracked tree. `requirements-dev-build0191a.txt` and `requirements-dev-build0192.txt` (root level)
are still referenced by `scripts/bootstrap-dev.sh` and `scripts/bootstrap-dev-build0192.sh`
respectively, plus historical `docs/BUILD-019.*` records and `CHANGELOG.md` —
`KEEP_HISTORICAL_EVIDENCE`, not orphaned.

### 8. Generated/accidental artifacts

**0 tracked.** `git ls-files` repo-wide confirms no `target/`, `node_modules/`, `dist/`, `build/`
directory, and no `.DS_Store`/`__pycache__/`/`*.pyc` file is tracked anywhere, including inside
`experiments/`, `tools/poc/`, `packaging/`, and the legacy PySide6 tree. `.gitignore` already covers
all of these (verified, not modified — no gap found, so no change made under §29).

### 9. Documentation staleness — the real cleanup work this milestone

This is where the actual, needed cleanup was: three "current status" documents had gone stale as
M1-M4 completed underneath them, plus one milestone's own human-validation record was never
synchronized after the fact.

- **`docs/migration/BUILD-025-M1-HUMAN-VALIDATION.md`**: still read `Status: PENDING` / `Result:
  PENDING` even though M2, M3, and M4 had all since built on top of an implicitly-passed M1 (the
  fix commit `d3c93b9` and M2's start, both 2026-08-13, only make sense if M1 had been
  re-validated PASS in between). Synchronized to **PASS** (Tester: Project Owner, Date:
  2026-08-13), consistent with this project's established "record only the reported overall
  result, don't retroactively check individual boxes" convention (already used for M2/M3). This is
  a documentation-sync correction, not a new validation round or a behavior change.
- **`docs/migration/BUILD-025-M4-HUMAN-VALIDATION.md`**: updated from `PENDING` to **PASS** (Tester:
  Project Owner, Date: 2026-08-13), per this M5 mandate's own explicit authorization recording M4
  Human Validation as PASS.
- **`README.md`**, **`ROADMAP.md`**, **`docs/migration/README.md`**: all three had "Build 025 IN
  PROGRESS" / "M4 engineering COMPLETE, Human Validation PENDING" framing. Updated to reflect M1-M5
  all COMPLETE, Build 025 COMPLETE, Desktop Feature Parity ESTABLISHED, and `Next: Build 026`.

No historical per-milestone document's own past-tense record was rewritten — only current-status
documents and the two human-validation tables above (which record a fact, not a narrative).

## Removed

**None.** No file, script, or code path met the `SAFE_TO_REMOVE` bar. This is expected, not a
shortfall: Builds 022-025 each closed with their own integration/consistency gate, so the
repository never accumulated the kind of drift a cleanup milestone usually exists to address.

## Retained Historical Evidence

`experiments/`, `tools/poc/` (TE-001/TE-002), all superseded per-milestone `validate-build*.sh`
scripts, `requirements-dev-build0191a.txt`/`requirements-dev-build0192.txt` and their bootstrap
scripts — all unchanged.

## Retained Legacy Reference

`src/zerorodcad_desktop/` (legacy PySide6 app) and its dedicated packaging/analysis scripts —
unchanged. **Legacy PySide modified: NO.**

## Deferred / Uncertain

None identified. Every candidate surfaced by the discovery pass resolved cleanly to `KEEP_*` or
`GENERATED_NOT_TRACKED` (n/a — nothing found); nothing required deferral.

## Other observations (not cleanup, no action taken)

Commit `e5e4962` (`feature/prototype-005-readonly-imap`, between the M3 and M4 commits on this
branch's history) has a commit message that does not match its content — its diff is legitimate
Build 025 M4 desktop-shell scaffolding (`menu.rs`, panel wiring, tests), not IMAP-related work,
almost certainly a copy-paste mistake into the commit message. Per this project's own rule (never
amend/rewrite already-merged history without explicit request), this was left untouched and is
noted here only for the record.

## Validation

This cleanup pass made no source-code, script, or contract change — only two human-validation
tables and three current-status documents were edited. `scripts/validate-build025.sh` (the new
Build 025 master gate, see [`BUILD-025-COMPLETION.md`](BUILD-025-COMPLETION.md) for its full run
record) includes an explicit repository-cleanup-integrity check (no `target/`/`node_modules/`/
`dist/`/`build/`/`.DS_Store`/`__pycache__`/`.pyc` tracked by git) so this invariant is now
continuously verified, not just asserted once here.

## Net Repository Impact

Files removed: 0. Code paths removed: 0. Scripts removed: 0. Docs removed: 0. Docs corrected: 5
(`BUILD-025-M1-HUMAN-VALIDATION.md`, `BUILD-025-M4-HUMAN-VALIDATION.md`, `README.md`, `ROADMAP.md`,
`docs/migration/README.md`). New docs added: this file and `BUILD-025-COMPLETION.md`. New script
added: `scripts/validate-build025.sh` (the Build 025 master gate, §38 of the mandate — not a
cleanup action, a required M5 deliverable).
