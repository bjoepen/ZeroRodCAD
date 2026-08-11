# Build 024 M3 — Export Robustness & Edge Cases

Status: **engineering COMPLETE / Gate BUILD-024-M3: PASS** — Human Validation **PENDING**.

## Objective

M1 proved the export boundary; M2 made it usable (and, after a Human-Validation-caught bugfix,
genuinely usable). M3 is not a feature milestone — it hardens the existing, already-working
export workflow against realistic failure modes, without redesigning any of it. The guiding
question throughout: **what happens when export does *not* take the happy path?**

## Baseline

- Build 022: COMPLETE / PASS (expected drift on the frozen `core:default`-only capability
  check, re-verified directly per the established pattern — not a regression).
- Build 023: COMPLETE / PASS (same expected drift).
- Build 024 M1: COMPLETE / PASS (same expected drift, plus the frozen "no export UI /
  engine-package changes since M1" checks — both legitimately touched by M2 and M3).
- Build 024 M2: COMPLETE / PASS, **including the post-Human-Validation bugfix**
  (`docs/migration/BUILD-024-M2-EXPORT-BUGFIX.md`) — `engine_export`/`engine_export_preflight`
  now correctly bind `output_directory` via `rename_all = "snake_case"`.
- M2 Human Validation: **PASS** (Round 2) — native directory selection works, export succeeds,
  STL/STEP/report are generated, the exported model opens successfully. This is real evidence
  M3 builds on, not something M3 re-proves from scratch.
- Working tree was clean at `fb53566` before this milestone began.

## Robustness inventory

Classified per the mandate's own taxonomy — **TESTED** (real, automated, non-mocked-below-the-
boundary-under-test), **SIMULATED** (a controlled test double at a documented, narrow
boundary), **CODE-INSPECTED** (verified by reading the actual code path, not executed under
the failure condition), or **NOT SAFELY TESTABLE** (would require unsafe manipulation of the
real environment; not attempted).

| # | Failure mode | Classification | Evidence |
|---|---|---|---|
| A | Destination disappears after selection | TESTED | `test_export_succeeds_even_if_directory_was_removed_after_a_prior_preflight` — not actually a failure; `export_project`'s own `mkdir(parents=True, exist_ok=True)` self-heals |
| B | Destination becomes unwritable | TESTED | `test_export_permission_denied_directory_returns_structured_error` (pre-existing, M1) |
| C | Expected output already exists | TESTED | M2's full preflight/overwrite test suite (pre-existing) |
| D | Partial exporter failure | CODE-INSPECTED + TESTED (verification layer) | See "Partial failure" below; `export_incomplete` tests cover the backstop |
| E | STL missing after `export_project` returns | TESTED | Backstop covered generically by the zero-byte test below (same code path) |
| F | STEP missing after `export_project` returns | TESTED | Same |
| G | Report missing | TESTED | Same |
| H | Zero-byte output | TESTED (SIMULATED injection) | `test_export_incomplete_when_a_written_output_is_zero_bytes` — monkeypatched, since CadQuery can't reliably be forced into this at the OS level |
| I | Invalid parameter payload | TESTED | Pre-existing + strengthened: `test_export_rejects_invalid_domain_parameters` now also asserts zero files written |
| J | Sidecar error (structured) | TESTED | Pre-existing full error-code test suite |
| K | Sidecar crash during export | CODE-INSPECTED | See "Sidecar crash & retry policy" below — no Rust-level crash-injection harness exists for *any* command in this codebase yet (not export-specific); building one is out of this milestone's narrow scope. Idempotency (the property that makes the existing generic retry policy safe) IS directly tested |
| L | Request timeout | CODE-INSPECTED | Generic, command-agnostic in `engine.rs`; unchanged; not command-specific, so no new test needed beyond what already exists structurally |
| M | Malformed export response | TESTED | New `export_result.rs` — 11 unit tests, real Rust-side structural validation |
| N | Project-name filename collision | TESTED | Pre-existing (M1/M2) + confirmed unchanged |
| O | Repeated export | TESTED | `test_export_overwrites_existing_output_files_in_place` (M1) + new `test_real_subprocess_repeated_export_stress` (20 real exports) |
| P | Cancellation before export | TESTED | Pre-existing M2 frontend/Rust tests, re-verified unaffected |
| Q | App shutdown during/after export | TESTED (real subprocess) | Every real-subprocess sequence test ends in `shutdown` + `returncode == 0` |
| R | Destination containing spaces | TESTED (real, both `.venv-novtk-poc` and the productive onedir binary) | `test_export_into_a_directory_with_spaces_succeeds`, `test_real_subprocess_paths_and_interleaving_sequence`, and the M3 validation script's packaging smoke test |
| S | Unicode destination path | TESTED (real subprocess) | `test_real_subprocess_paths_and_interleaving_sequence` (directory name), `test_export_unicode_project_name_succeeds_end_to_end` (project name) |
| T | Long but reasonable destination path | NOT SAFELY TESTABLE (not separately exercised) | No length-specific test added — nothing in the export path imposes an artificial length limit (plain `pathlib`/OS calls throughout), and no evidence of a real length-related defect was found; not claimed as empirically verified |

## Post-export verification (§8) — reviewed, preserved, strengthened

M1's sidecar-side post-export verification (`path.is_file() and path.stat().st_size > 0` for
all three expected outputs) is unchanged and still the authoritative backstop against
CadQuery's documented silent-no-op behavior. M3 adds a **second, independent layer** at the
Rust/Tauri boundary (`export_result.rs`) that structurally validates the *shape* of whatever
the sidecar returns before it can ever reach the WebView as a success value — this is new
ground the sidecar-side check doesn't cover (a correctly-verified sidecar result could still be
serialized/transported incorrectly, or a future sidecar change could accidentally omit/rename a
field). Both layers are real, both are tested, neither duplicates the other's logic.

## Basic format validation (§9)

Investigated what the actual export formats are (not assumed): `cadquery.exporters.export`
writes **binary** STL (confirmed — the existing evidence in
`BUILD-024-M1-EXPORT-FOUNDATION.md` and this milestone's own byte-content tests handle it as
binary throughout, never assuming ASCII framing), and `Assembly.export(...)` writes STEP
(`ISO-10303-21` — confirmed directly by inspecting real exported file content during this
milestone's investigation, see "Sidecar crash & retry policy" below). No new format-sanity
check was added beyond the existing non-empty/exists check: a real per-format structural check
(binary STL primitive-count validation, or STEP `ISO-10303-21`/`END-ISO-10303-21` header/footer
markers) was considered but not implemented in M3, since the existing non-empty-file check
already catches the *actual observed* CadQuery failure mode (silent no-op → zero-byte or
missing file), and a deeper per-format parser was explicitly out of scope ("No new CAD parser
dependency"). Flagged as a possible, narrow future addition (§9 already anticipates this), not
implemented here because no evidence currently justifies the added complexity.

## Corrupt/incomplete success (§10) — hard invariant re-confirmed

Both verification layers (sidecar post-export check, Rust structural validation) mean: **a
`success` state can only ever be reached in the frontend after both the sidecar itself and the
Rust IPC boundary have independently confirmed the result is complete and well-formed.** No
code path allows `export_project` returning without raising to produce a false "ok": true —
this was already M1's own finding and remains true; M3 only adds the second, independent Rust
layer as additional depth.

## Partial failure (§11/§12)

Exact existing order, confirmed unchanged by re-reading `export_project`:

```text
1. exporters.export(build_body(parameters), body_path)       # STL
2. build_assembly(parameters).export(assembly_path)          # STEP
3. save_report(report_path, parameters)                      # report.md
```

Not transactional (unchanged M1 finding). If STL succeeds and STEP fails: one real file
remains on disk. If STL+STEP succeed and the report write fails (the one write CadQuery
doesn't silently swallow — a plain `Path.write_text`): two real files remain. **M3 policy
(§12): preserve whatever was written, report the failure/incompleteness explicitly, identify
which output(s) are missing, and do not attempt any rollback or deletion of partially-written
(but individually valid) files.** No transactional rewrite was implemented — the existing
`export_incomplete` structured error with a `details.missing` list already gives the user
(and, downstream, `export_panel.ts`'s error message) exactly what's needed to decide what to
do next, without inventing new complexity or risking deleting a file a user might still want.

## Overwrite robustness (§13) — stress-tested

All of no-conflict / one-conflict / all-outputs-conflict / project-name-collision / repeated
export / changed-geometry-into-same-target / cancel / confirm were already covered by M2's own
test suite (`test_export_preflight_reports_one_conflict`,
`test_export_preflight_reports_multiple_conflicts_partial`,
`test_export_preflight_sanitized_project_name_collision_detected`,
`test_export_overwrites_existing_output_files_in_place`, plus the frontend's
`export_panel.test.ts` overwrite-conflict-flow suite and the real end-to-end
`test_real_subprocess_preflight_overwrite_confirm_sequence`). M3 re-ran all of them
unmodified (still green) and did not find a gap requiring a new overwrite-specific test.

## TOCTOU — preflight vs. write (§14) — investigated, no code change

There is a real, unbounded time gap between `export_preflight` reporting "no conflict" (or the
user confirming an overwrite) and the actual `export` call — the confirm path in particular
waits on human interaction with no time bound at all. **Investigated scenario**: a file
appears in the destination between preflight and the real export call. **Finding: this
already reduces to the product's existing, deliberate silent-overwrite-in-place behavior** —
even without any preflight at all (M1's original behavior), `export_project` always silently
overwrites whatever's there. A TOCTOU race in the "no conflict" path therefore has exactly the
same worst-case outcome as the pre-preflight product already accepted: the user isn't warned
about a conflict that appeared in that narrow window, but nothing is corrupted, and no
worse outcome than "M1 without preflight" occurs. The wider case — the destination directory
itself disappearing or becoming unwritable during the gap — is already handled independently
by `export_project`'s own error handling (`mkdir` self-heals a missing directory;
permission/write errors are already mapped to structured errors) at the moment of the actual
write, regardless of how long the gap was. **Decision: no backend recheck was added.** The
narrow race's worst case already matches accepted product behavior, and a recheck would add a
second preflight round trip (plus its own, smaller TOCTOU gap between recheck and write) without
changing the actual worst-case outcome. Documented here per the mandate's explicit "document
the race honestly" instruction — this is a conscious decision, not an oversight.

## Path robustness (§15-19)

- **Destination disappears**: TESTED — see inventory row A. Not a failure case; self-heals.
- **Destination becomes unwritable**: TESTED (pre-existing M1 test, permissions restored in a
  `finally` block even on assertion failure).
- **Downloads/Documents**: constrained by this environment having no interactive OS Save-panel
  access; the *real* native-dialog directory selection into a real user folder was already
  proven by M2's own real Human Validation (Round 2 PASS). M3 adds `~/Downloads`/`~/Documents`
  items to the human checklist below as an explicit regression-style retest, not a new claim of
  automated coverage for the dialog itself.
- **Spaces in path**: TESTED, real, twice — once against `.venv-novtk-poc`
  (`test_export_into_a_directory_with_spaces_succeeds`,
  `test_real_subprocess_paths_and_interleaving_sequence`) and once against the actual
  productive PyInstaller onedir binary (this milestone's validation script's packaging smoke
  test). No shell is ever involved in the export path (confirmed by inspection — `subprocess`/
  `tauri_plugin_shell`'s `Command::spawn` argv-based invocation, `pathlib.Path`, direct file
  writes — no shell string ever constructed from a directory name), so no escaping concern
  exists structurally, not just empirically.
- **Unicode path**: TESTED, real, against `.venv-novtk-poc`
  (`test_real_subprocess_paths_and_interleaving_sequence` uses `"ZeroRod – Prüfung"` as a real
  directory name). Path is forwarded unmodified throughout — no normalization applied anywhere
  in the pipeline (confirmed by inspection of `select_export_directory`, `commands.rs`,
  `_run_export_command`/`_run_export_preflight_command`).

## Project-name edge cases (§20/§21)

- Ordinary ASCII, punctuation, and collision cases: pre-existing (M1/M2), re-verified green.
- Unicode: new, real, end-to-end (`test_export_unicode_project_name_succeeds_end_to_end`) —
  confirms the documented M1 finding (Unicode letters kept lowercase as-is, not
  transliterated) holds through the *actual* export pipeline, not just the pure
  `_safe_name`/`expected_output_filenames` unit level.
- Empty/pathological safe name (§21): **reachable** — `project_name` has no domain-level
  validation rule (confirmed by inspecting `validation.py`; the field simply doesn't appear
  there), so an empty or whitespace-only `project_name` reaches `export_project` unfiltered.
  **Not unsafe**: `_safe_name`'s existing fallback (`"zerorod"` when sanitization produces an
  empty string) already handles it correctly and was already unit-tested at the pure-function
  level (M1). M3 adds the missing end-to-end proof
  (`test_export_empty_project_name_falls_back_to_zerorod_end_to_end`) that this fallback
  actually produces real, valid, non-empty output files through the full pipeline, not just a
  correct string. **No defect found; no fix needed; no naming redesign performed.**
- **Hard invariant re-confirmed**: `test_export_preflight_filenames_match_actual_export_output`
  (pre-existing) continues to prove preflight's expected filenames exactly match what export
  actually produces, for arbitrary project names — unaffected by any M3 change (both still
  route through `zerorodcad.export.expected_output_filenames`).

## Invalid parameters (§22)

`test_export_rejects_invalid_domain_parameters` (pre-existing) was strengthened with an
explicit assertion that **zero files are written** for a domain-invalid request — this was
already true by construction (Level 3 validation runs and raises before `export_project` is
ever called), but was not previously asserted directly. `test_export_valid_after_a_failed_export_request`
(pre-existing) continues to prove the sidecar survives and a subsequent valid export succeeds.

## Malformed sidecar response (§23)

New: `desktop/src-tauri/src/export_result.rs`, 11 unit tests. `engine_export` and
`engine_export_preflight` now validate the sidecar's JSON result structurally before it can
ever reach the WebView — missing `output_directory`, missing/wrong-typed `files`, a missing
expected role, an unexpected role, a missing `path`, `files`/`expected_files`/`conflicts` as
the wrong JSON type, and an internally-inconsistent `has_conflicts` vs. `conflicts` are all
caught and mapped to a new `invalid_export_result` structured `EngineError` — never a crash,
never a false success. The productive sidecar itself was **not** modified to intentionally
misbehave (per the mandate's explicit instruction) — this is pure boundary-code defense, tested
with hand-constructed JSON fixtures at the Rust unit level, exactly mirroring the established
`mesh::validate_and_summarize` pattern for `zerorod-mesh/v1`.

## Sidecar crash & export retry policy (§24-26) — the critical M3 question

**Current behavior (unchanged, `engine.rs`)**: `engine::request` is entirely generic across
commands — on a detected crash (`sidecar_crashed`) or timeout, it kills the dead process,
respawns, and retries the *exact same request* exactly once, regardless of which command it
was. This was designed before productive export existed and was never reconsidered for a
side-effecting (filesystem-writing) command until now.

**Investigation**: no Rust-level crash-injection test harness exists in this codebase for
*any* command (not export-specific) — `engine::request`'s crash-retry branch has never been
unit-tested directly, since exercising it for real requires a real spawned OS child process
whose termination timing can't be precisely controlled from a `MockRuntime`-based test without
either (a) modifying `engine.rs` itself (an explicitly cross-build-frozen invariant this
repository's own gates check) to accept an injectable test double, or (b) new, substantial test
infrastructure disproportionate to this milestone's narrow scope. This was evaluated and
deliberately not built.

**What *was* directly, empirically tested**: whether a retry (i.e., calling `export_project`
again with the identical request) can ever produce a corrupted or incorrect result.
`export_project` always fully rewrites every output file from scratch (`exporters.export`,
`Assembly.export`, and `save_report` are each single, complete writes — never append, never
partial-update). Empirically (`test_export_repeated_identical_parameters_produce_consistent_output`):
calling export twice with identical parameters into the same directory produces **byte-identical
STL and report** output — proving no cumulative or randomized state affects those two writers.
**One genuine, newly-discovered nuance**: the STEP assembly export is *not* byte-identical
across repeated calls with identical parameters — CadQuery/OCP's STEP writer assigns internal
entity IDs and `STYLED_ITEM`/`COLOUR_RGB` references in an order that isn't guaranteed stable
across repeated `Assembly.export()` calls in the same process (directly observed: a handful of
differing `NEXT_ASSEMBLY_USAGE_OCCURRENCE`/`STYLED_ITEM`/`COLOUR_RGB` entity lines out of
~2,200, same file size, same overall structure). This was verified directly (not assumed) and
is now the test's own documented finding, not swept aside.

**Decision (Option A, evidence-based): the existing generic retry-once policy is safe to leave
unchanged for `export`, including its side effects.** Rationale: a retry can never leave a
destination in a *worse* state than a single successful export would — every write is a
complete, from-scratch overwrite (never partial/corrupted), the geometry-defining content is
correct for the requested parameters either way, and the only observed retry-vs-original
difference is cosmetic STEP-internal metadata numbering/ordering, not incorrect geometry or file
corruption. No command-specific retry-suppression logic was added to `engine.rs` (which remains
byte-for-byte unchanged since M1, `f2a7ce9`) — introducing one would be new, untested complexity
to guard against a risk the evidence doesn't actually support. **Preview's retry behavior is
unaffected** (it was never touched — the policy is generic, unchanged, and this decision keeps
it that way for both commands rather than special-casing either one).

## Timeout safety (§27/§28)

Unchanged: `REQUEST_TIMEOUT_SECS = 30`, generic across commands. Re-measured export timing this
milestone (see Performance below) — still ~0.13 s warm, ~200x margin under timeout, no new
evidence to change it. What happens if a timeout *does* occur during export: `engine::request`
treats it identically to a crash — kills the process, respawns, retries once. The same
idempotency/no-corruption reasoning from the retry-policy section above applies; a timed-out
export's retry cannot produce a worse outcome than a single successful export. No new
timeout-injection test was built, for the same "no existing harness, disproportionate new
infrastructure for this milestone" reason as the crash-injection case — classified
CODE-INSPECTED, not empirically TESTED, and documented as such rather than claimed otherwise.

## Disk full (§29)

Real OS-level disk-full remains **NOT SAFELY TESTABLE** in this environment (would require
either filling a real disk or constructing a loopback filesystem image, both explicitly
disallowed by the mandate). What *is* now tested: the error-mapping path at the exact write
boundary, via a monkeypatched `export_project` raising `OSError(errno.ENOSPC, ...)`
(`test_export_write_failed_maps_a_simulated_disk_full_oserror`) — confirms `export_write_failed`
is correctly produced and that zero files remain written for this specific injected failure.
**Classification: SIMULATED at the error-mapping boundary, not empirically verified against a
real full disk** — stated honestly, not claimed as full coverage.

## Repeated export stress (§31)

`test_real_subprocess_repeated_export_stress`: 20 real, sequential export requests against the
real persistent `.venv-novtk-poc` interpreter, cycling across 4 destinations (so both fresh
writes and real overwrites are exercised), followed by one more `preview` and a clean
`shutdown`. All 22 requests succeed; all final files are valid and non-empty;
`returncode == 0`. Memory growth over the same shape of sequence is measured separately (see
Memory below) rather than duplicated into this correctness-focused test.

## Preview/export interleaving (§32)

`test_real_subprocess_paths_and_interleaving_sequence`: `preview(defaults) → export(defaults,
spaces-path) → preview(body_width=60) → export(body_width=60, Unicode-path) → preview →
shutdown`. Directly confirms **export-2's report contains `60.00 mm`, not the stale `38.00 mm`**
— proving the export always reflects the parameters *of that specific export call*, never a
stale prior preview/export's geometry. No queue corruption observed across the sequence.

## UI error recovery (§33/§34/§35)

`export_panel.test.ts` gained four new tests this milestone:

- A malformed/rejected export result (the new `invalid_export_result` code) never renders as
  `success` — surfaces as a concise error instead.
- A stale error clears once a subsequent export attempt succeeds (full state transition, not a
  residual leftover error alongside a new success).
- A stale cancellation note clears once a new export attempt succeeds.
- `engine_export_preflight` rejecting with `invalid_export_result` is a structured error, not a
  crash, and `requestExport` is never called for it (no export attempted on top of a broken
  preflight result).

Cancellation (dialog and overwrite) remain unchanged and still non-error, re-verified by the
existing (unmodified, still green) M2 test suite. Success continues to render only backend-
supplied filenames — no frontend reconstruction, unchanged from M2, now further guarded by the
Rust structural-validation layer described above.

## Security invariants (§36)

Unchanged from M2: WebView capability is exactly `["core:default", "dialog:allow-open"]`, no
`fs:*`, no `shell:*`/`process:*`, no `dialog:allow-save/message/ask/confirm`, CSP unchanged. M3
added **zero** new capabilities — `export_result.rs`'s validation is pure in-process JSON
structure checking, requiring no additional permission of any kind.

## Contract invariants (§37/§38)

`zerorod-parameters/v1`, `zerorod-sidecar/v1`, `zerorod-mesh/v1`: unchanged. No protocol v2.
The `invalid_export_result` error code is additive within the existing structured-error
envelope (`{code, message, details?}`) — no shape change, no new envelope field.
`zerorodcad.export.export_project` remains canonical and was not modified this milestone (only
`export.py`'s M2-era `expected_output_filenames` helper exists alongside it, unchanged since
M2). `model.py`/`report.py`/`parameters.py`/`validation.py` are all byte-for-byte unchanged
since M1 (`f2a7ce9`) — verified directly by this milestone's own validation script.

## Performance (§44)

Re-measured against the real `.venv-novtk-poc` persistent process:

| Scenario | M1/M2 baseline | M3 measurement |
|---|---|---|
| `export`, cold-ish first call | ~1.45 s (M1) | 0.128 s (already-warmed process — consistent with M2's own finding that a session's first `preview` typically warms CadQuery before the first export) |
| `export`, warm | ~0.13 s | 0.128 – 0.142 s (3 consecutive calls) |
| `export_preflight`, full process round trip incl. cold interpreter start | 0.036 s (M2) | consistent, no regression |

No material regression. The new Rust-side structural validation (`export_result.rs`) is pure
in-memory JSON traversal on an already-small payload (a handful of fields) — not separately
benchmarked, as its cost is negligible relative to the ~0.13 s sidecar round trip it sits next
to.

## Memory (§45)

Bounded 20-export sequence against the real persistent process, RSS sampled via `ps`:

| Checkpoint | RSS |
|---|---|
| After request 1 | 324,720 KB |
| After request 5 | 331,936 KB |
| After request 10 | 337,088 KB |
| After request 15 | 339,984 KB |
| After request 20 | 341,168 KB |

**Growth: +5.07% over 20 export requests (324.7 MB → 341.2 MB), tapering** — the growth rate
from request 5 to request 20 (15 further exports) is only +2.8%, versus the larger jump from
request 1 to request 5, consistent with warm-up caching (CadQuery/OCP internal object pools)
stabilizing rather than an unbounded per-call leak. Reported honestly, not rounded down to
"no growth": this is measurably higher than Build 023 M4's own ~0.18% growth over 20 *preview*
requests (a much lighter operation — no file I/O, no STEP assembly export), which is expected
given export's heavier per-call work, not a sign of the same kind of steady-state behavior.
No further endurance testing was performed, per the mandate's own "no need for unrealistic
endurance testing" allowance — this is enough to detect an obvious leak, and none was found.

## Packaging (§46)

Fresh release build from this exact M3 HEAD, via the established
`scripts/build-productive-desktop-app.sh release` pipeline (PyInstaller onedir, Tauri release,
hash-gated dylib dedup, no onefile). See the final report for the exact measured bundle size —
expected consistent with the M2 baseline (~285.9 MiB), since M3 added no new Cargo dependency,
no new sidecar dependency, and no packaging-spec change.

## Tests

- **Python**: `test_export.py` (unchanged, still green), `test_zerorod_sidecar_main.py` (+9
  new: zero-byte detection, simulated disk-full mapping, empty-project-name end-to-end,
  Unicode-project-name end-to-end, spaces-path export, directory-disappears-after-preflight,
  repeated-identical-parameters consistency, plus the strengthened invalid-domain-parameters
  test), `test_zerorod_sidecar_persistent.py` (+2 real-subprocess tests: paths/interleaving,
  20x repeated-export stress). Full repository suite: **347 passed, 1 skipped** (the skip is
  the pre-existing, unrelated TE-001 Gate-A re-evaluation note) — up from 338 at the M2
  baseline. Ruff clean.
- **Rust**: new `export_result.rs` module (11 unit tests). Full suite: **42/42 passed** (up
  from 31 at the M2 baseline). `cargo fmt --check`/`cargo clippy --all-targets -- -D warnings`
  both clean.
- **Frontend**: `export_panel.test.ts` (+4 new: malformed-result handling, stale-error-clears-
  on-retry, stale-note-clears-on-retry, preflight-malformed-result handling). Full suite:
  **207 passed, 1 skipped** — up from 203 at the M2 baseline. TypeScript clean, production
  build clean.

## Known limitations

1. Real sidecar-crash-during-export and real request-timeout-during-export remain
   CODE-INSPECTED, not empirically TESTED — no Rust-level crash/timeout-injection harness
   exists for any command in this codebase (not export-specific), and building one would
   require either modifying `engine.rs` (a cross-build-frozen invariant) or substantial new
   test infrastructure disproportionate to this milestone. The retry-safety *conclusion* is
   evidence-based (idempotency of the underlying writes, directly tested); the crash-detection
   *mechanism* itself is not separately re-verified here — it was already an unchanged,
   pre-existing part of `engine.rs`.
2. Real OS-level disk-full remains NOT SAFELY TESTABLE; only the error-mapping boundary is
   verified (SIMULATED), per M1's own original classification, unchanged.
3. STEP export is not byte-identical across repeated identical-parameter exports (newly
   discovered, documented above) — believed cosmetic (internal entity numbering/ordering,
   not geometry), but this was not independently verified beyond the direct line-diff performed
   during this investigation. Not treated as a defect requiring a fix (no evidence of incorrect
   geometry), but flagged honestly as an open, unquantified question rather than dismissed.
4. No STL/STEP format-level structural sanity check (header/footer markers) was added — the
   existing non-empty-file check already catches the one real, observed CadQuery failure mode.
   Flagged as a possible narrow future addition, not implemented (no new CAD parser dependency
   introduced).
5. Long-path testing (§7 row T) was not separately exercised — no evidence of a length-related
   defect exists in the current code path (no artificial limits), but this was not empirically
   proven either.

## M4 handoff

Per the mandate, M3 does not start M4. M4's expected purpose (per the mandate's own framing) is
**Integration & Build Completion** — a milestone-consistency and architecture-conformance audit
across M1-M3, not another feature milestone, unless M3 uncovered a real blocking defect (it did
not: no false-success path exists, retry is evidence-supported as safe, overwrite/cancel remain
safe, and all prior gates remain green). M4 requires explicit Project Owner approval to start,
per the mandate's own stop condition, and should begin only after this milestone's Human
Validation (below) is complete.

## Gate BUILD-024-M3

**PASS** (engineering). See `scripts/validate-build024-m3.sh`; final line
`BUILD-024-M3 CONSISTENCY GATE: PASS`. Human Validation remains **PENDING**
(`docs/migration/BUILD-024-M3-HUMAN-VALIDATION.md`).
