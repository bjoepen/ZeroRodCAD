# Build 026 / Milestone 1 — Production Bundle Hardening & Reproducibility

## Scope

M1 closes the Discovery-identified `REQUIRED_FOR_DISTRIBUTION` gaps that don't require Apple
Developer credentials: the CadQuery No-VTK clean-machine reproducibility break, bundle metadata
(identifier, minimum macOS, stale `LSRequiresCarbon`), the two obsolete PyInstaller hiddenimports,
loose dependency/toolchain pinning, and CI Stage 1 (build-only, no secrets). No product feature,
no signing, no notarization, no PySide6 change. Full milestone authorization:
`docs/migration/BUILD-026-GAP-REPORT.md` (Discovery) plus the Project Owner's Decision Resolution &
M1 Authorization message.

## Decisions Resolved (recap)

| Decision | Value |
|---|---|
| Bundle identifier | `de.zerorodcad.desktop` (replaces `dev.zerorodcad.desktop`) |
| Minimum macOS | See "Minimum macOS Version — a materially different finding than assumed" below |
| Public product version | `0.1.0` (unchanged) |
| Engineering identity | Build `026` / Milestone `M1` |
| Architecture | ARM64 only (Universal2 deferred) |
| Primary distribution artifact | DMG (M2 scope, not built in M1) |

## No-VTK Reproducibility — the primary M1 objective

### Previous hidden prerequisite

`scripts/validate-te0012-novtk-bundle.sh` provisioned the shared productive build venv
(`.venv-novtk-bundle`) by `cp`-ing 4 already-patched CadQuery files out of a **separate, sibling
venv**, `.venv-novtk-poc`. `.venv-novtk-poc` is created by `scripts/validate-te001-novtk.sh`, but
that script installs **vanilla, unpatched** `cadquery==2.8.0` — no tracked script anywhere in the
repository ever applied the actual VTK-import-removal patch to `.venv-novtk-poc`. Its patched state
existed only as undocumented, hand-applied local machine state with no reproducible provenance. The
4 tracked `.diff` files under `docs/research/TE-001.1-CadQuery-NoVTK/patches/` were themselves only
a **historical record** — diffs generated *from* that already-patched venv against a scratchpad copy
of the originals — never something any script actually applied.

### New mechanism

`scripts/apply-cadquery-novtk-patch.sh <venv-python>`: applies the 4 tracked unified diffs directly
to a target venv's freshly `pip install`ed, unpatched `cadquery==2.8.0`, with:

- **Idempotency**: pre-checks each of the 4 target files for a top-level `vtkmodules`/`OCP.IVtk*`
  import; if all 4 are already absent, no-ops (safe to re-run). An inconsistent partial-patch state
  (some files patched, some not) is refused rather than guessed at.
- **Fail-fast on content mismatch**: `patch --fuzz=0` inherently validates the diff's context lines
  against the actual file content before applying anything — a version mismatch or unexpected
  upstream change aborts the whole application with a clear message, never a silent partial patch.
- **Post-patch verification**: re-checks all 4 files for the same top-level-import marker, then
  actually imports `cadquery` under the existing `VTKImportBlocker` test harness
  (`tools/poc/novtk/vtk_import_blocker.py`) to functionally prove the patch is effective, not just
  textually applied.

`scripts/provision-novtk-bundle-venv.sh [venv-path]` is the new single, authoritative provisioning
entry point: creates the target venv from scratch if needed, installs the full pinned dependency
list, and calls `apply-cadquery-novtk-patch.sh` — no reference to `.venv-novtk-poc` anywhere.
`scripts/validate-te0012-novtk-bundle.sh` (the TE-001.2 legacy-app validation script that also
provisions this shared venv) now calls the same script instead of its old `cp` block, so both the
Tauri productive path and the legacy TE-001.2 path use one, identical, tracked mechanism.
`scripts/build-productive-desktop-app.sh`'s missing-venv error message now points here.

### Patch provenance / a real defect found and fixed

Applying the 4 tracked `.diff` files with a standard `patch`/`git apply` against a byte-identical
fresh install **failed** — `patch: **** malformed patch` / `git apply: corrupt patch`. Root cause:
several blank **context** lines (representing an unchanged blank line in the file) were missing
their required leading space marker — a valid unified-diff context line must start with a literal
space character even when the line itself is empty; these had been silently stripped, most likely by
whatever tool originally saved/copied the diff text. This is a genuine defect in the tracked patch
files, not a tooling incompatibility. Fixed by restoring the missing leading space on exactly the
affected lines (7 in file 1, 1 in file 2, 5 in file 3, 7 in file 4 — 20 total), touching no `+`/`-`
diff content, only the blank-context-line marker.

### Patch verification — pinned source, exact-match proof

- **Source pinned**: `cadquery==2.8.0` (exact), matching the version already pinned everywhere else
  in the productive dependency chain.
- **Pre-patch state verified**: `patch --fuzz=0`'s own context-matching is the verification — it
  refuses to apply against content it doesn't recognize.
- **Post-patch state verified**: no top-level VTK import remains (grep) + `import cadquery` succeeds
  under `VTKImportBlocker` (functional).
- **Exact-match proof**: applying the (repaired) 4 diffs to a **completely fresh, isolated scratch
  venv** (`python3.13 -m venv` + `pip install cadquery==2.8.0 --no-deps`, no relation to any
  productive or PoC venv) produced files **byte-for-byte identical** (`diff -q`, 0 differences
  across all 4 files) to what was already shipping in the productive `.venv-novtk-bundle` before
  this milestone — proving the new mechanism reproduces exactly the accepted, already-validated
  patch content, not a reinterpretation of it.

### Clean environment — real deletion/recreation, not a reused environment

The strongest available proof was performed for real, not simulated:

1. `.venv-novtk-bundle` was deleted entirely (`rm -rf`).
2. `.venv-novtk-poc` was **moved off the filesystem entirely** (not just left unreferenced in code)
   for the duration of the test, so no code path could possibly reach it even by accident.
3. `scripts/provision-novtk-bundle-venv.sh` was run from scratch with `.venv-novtk-poc` absent —
   **PASS**: fresh venv created, pinned dependencies installed, patch applied and verified.
4. `.venv-novtk-poc` was moved back afterward (reversible; it remains a legitimate, separate TE-001
   artifact, untouched in content).
5. `scripts/build-productive-desktop-app.sh release` was run against the freshly reproduced venv —
   **PASS**: productive `.app` built successfully, no hidden-import warnings (see below), same
   287 MiB / 201 files / 57 dirs / 77 symlinks / 161 Mach-O shape as every prior Build 022–025
   measurement.

### A second, independent defect found: `.gitattributes` was silently corrupting the patches on commit

While staging this milestone's changes, `git add` warned it would replace CRLF with LF in the patch
files. Investigation traced this to the repository's own `.gitattributes` (`* text=auto eol=lf`,
with no override for these files): every previous commit of these 4 diffs had been silently
LF-normalized in the git object store itself, even though the **working tree** copies (never
re-checked-out since their original commit) still carried the correct CRLF bytes needed to match
upstream cadquery's CRLF-line-ended source. This is exactly the kind of defect the fresh-environment
proof above is designed to catch — but only if it operates on a real checkout of the committed
object, not the working tree in its current, possibly-stale state. Verified directly:
`git show HEAD:<path>` (the object actually stored in history) already lacked the CR characters the
working-tree file had. **A real fresh clone would have received the corrupted, LF-only diffs and the
new patch mechanism would have failed again**, defeating the entire point of this milestone.

Fixed by adding a scoped `.gitattributes` override —
`docs/research/TE-001.1-CadQuery-NoVTK/patches/*.diff -text` — disabling all line-ending
normalization for these 4 files specifically, alongside the repository's existing binary-asset
exceptions (`*.stl`, `*.step`, etc.). Verified with `git checkout-index --prefix=<scratch>/ -a -f`
(a true index→working-tree materialization, exactly what a fresh clone's checkout performs) against
the staged index: the CR characters are correctly preserved in the materialized copy.

### Result

**PASS.** The productive build no longer depends on any undocumented, hand-patched local venv state,
and the tracked patch files themselves are now protected from the repository's own line-ending
normalization silently corrupting them again on a future commit.
A fresh clone, given a clean `.venv-novtk-bundle`/`.venv-novtk-poc` absence, now reproduces the
identical, already-validated No-VTK CadQuery patch through a single tracked, idempotent,
fail-fast, functionally-verified script.

## Minimum macOS Version — a materially different finding than assumed

The M1 authorization's Decision 2 assumed macOS 11.0 was achievable ("the first distributable
ZeroRodCAD release is ARM64-only, and Apple Silicon starts with macOS 11") but explicitly required
empirical verification against the actual dependency chain, with an instruction not to fake
compatibility if a real dependency requires more. **That verification found a materially higher
genuine floor than assumed:**

A full scan of all 161 Mach-O files in the freshly rebuilt bundle, reading each one's real
`LC_BUILD_VERSION`/`LC_VERSION_MIN_MACOSX` load command, found:

| `minos` | File count | Source |
|---|---|---|
| 11.0 | 41 | Rust/Tauri main executable, sidecar executable, most system-framework-linked code |
| 11.1 | 51 | OpenCASCADE `libTK*` dylibs, the `OCP` extension (their PyPI wheel's own build target) |
| 14.0 | 13 | `numpy`'s official PyPI arm64 wheels (numpy's own current minimum build target) |
| **26.0** | **56** | **`Python.framework` itself (the interpreter binary and its `Versions/3.13/Python`), the entire Python 3.13 standard-library extension-module set (`termios`, `zlib`, `unicodedata`, `_asyncio`, …), and `libssl`/`libcrypto`/`libmpdec`** |

Root cause of the dominant `26.0` figure: the packaging venv's Python 3.13 interpreter is Homebrew's
`python@3.13` bottle. Homebrew bottles are built with `MACOSX_DEPLOYMENT_TARGET` pinned to the macOS
version they were built for — on this machine, that is macOS 26 ("Tahoe"), the host OS itself. This
is standard, expected Homebrew behavior, not a defect this project introduced — but it means the
productive Python interpreter (and everything statically tied to its deployment target: the
interpreter binary, the full stdlib native-extension set, and the three OpenSSL/decimal libraries it
links) genuinely cannot be claimed compatible with any macOS release older than 26.0, and would
**fail to launch**, not just show a metadata inconsistency, on an older system.

A second, independent, smaller constraint exists regardless of the Homebrew issue: `numpy`'s own
official PyPI arm64 wheels currently target macOS **14.0** as their minimum — so even a
hypothetically portable, non-Homebrew Python 3.13 build would not by itself bring the genuine floor
below 14.0 without an unplanned numpy-from-source rebuild.

**Per the mandate's own explicit instruction ("DO NOT fake compatibility... use the highest genuine
minimum required by the productive dependency chain"), `LSMinimumSystemVersion` /
`bundle.macOS.minimumSystemVersion` was set to `26.0`** — the honest value for the current productive
toolchain — rather than the originally assumed `11.0`. This is flagged as the single most consequential
finding of this milestone, superseding Decision 2's premise with hard evidence.

**This is not accepted as a final answer.** Shipping a "minimum macOS 26.0" distributable is very
likely impractical for a real release audience and should not be treated as settled — it is reported
here, honestly, as this milestone's evidence-based result, with an explicit recommendation that a
follow-up task evaluate a non-Homebrew, portable-deployment-target Python 3.13 distribution for the
*packaging venv specifically* (e.g. python.org's official installer, or `python-build-standalone`),
which independent evidence suggests could bring the genuine floor down to roughly macOS 14.0 (numpy's
own floor) — not attempted in this milestone, since swapping the packaging interpreter is a real
toolchain change with its own compatibility risk (ABI matching against `cadquery-ocp-novtk`'s
`cp313-cp313-macosx_11_0_arm64`-tagged wheel, etc.) that exceeds "pin dependencies" scope and was not
explicitly authorized. **DECISION_REQUIRED.**

`LSRequiresCarbon` was confirmed a `tauri-bundler`/`cargo-bundle`-lineage default-template artifact
(Carbon is a pre-OS X, non-arm64-capable API family this Rust/WebKit app cannot possibly require) and
removed via a new `desktop/src-tauri/Info.plist` override file (Tauri merges this over its generated
defaults) — verified `false` in the actual compiled `Contents/Info.plist`, not just in source
configuration.

## Bundle Identifier

`desktop/src-tauri/tauri.conf.json`'s `identifier` changed from `dev.zerorodcad.desktop` to the
approved `de.zerorodcad.desktop`. Repository-wide inventory (`git grep`) found exactly one other
live reference to the old value — none; the only other occurrence anywhere in tracked source was
`experiments/te002-tauri/src-tauri/tauri.conf.json`'s own distinct identifier
(`dev.zerorodcad.te0021`), which is a different, protected, untouched PoC artifact, not the productive
app. Historical Build-022 and Build-026-discovery documentation still correctly quote the old value
in their own past-tense record — not rewritten, per standing project convention (historical records
are not retroactively edited). Verified in the actual compiled `Contents/Info.plist`
(`CFBundleIdentifier`), not source configuration alone.

## PyInstaller Hiddenimports Cleanup

`OCP.TKernel` and `cadquery.exporters` removed from `packaging/tauri/sidecar-onedir.spec`'s
`hiddenimports` list, per the Discovery audit's `OBSOLETE_HIDDEN_IMPORT` classification for both
(full root-cause analysis: `docs/migration/BUILD-026-DEPENDENCY-AUDIT.md`). Regression proof: a real
rebuild of the productive sidecar produced **zero** `Hidden import ... not found` warnings (previously
2 per build), and the full real end-to-end pipeline exercise (status, preview ×3, report, project
save/open roundtrip, export ×2, all producing valid non-empty STL/STEP/report output) passed against
the rebuilt sidecar — proving the removal changed nothing functionally.

## Toolchain / Dependency Pinning

- `casadi` and `runtype` — previously **completely unpinned** in the provisioning script — now pinned
  exactly to `casadi==3.7.2` / `runtype==0.5.3`, the versions the productive bundle has been built and
  validated against throughout Build 022–026.
- `scipy`/`numba` remain excluded from the shipped bundle (unchanged PyInstaller exclude rule); their
  build-venv install versions were left as previously resolved (not pinned further) since they never
  reach the shipped artifact — pinning them would add churn without a corresponding reproducibility
  benefit.
- `desktop/src-tauri/rust-toolchain.toml` added, pinning the Rust channel to `1.97.1` (the version
  this milestone's build was validated against) plus `rustfmt`/`clippy` components (both already used
  by the existing gate scripts).
- `desktop/frontend/.nvmrc` added, pinning Node to major version `24` (matching this milestone's
  validated build).
- `Cargo.lock` and `desktop/frontend/package-lock.json` were already git-tracked and registry-only —
  confirmed unchanged, no action needed (Discovery's `ALREADY_COMPLETE` classification stands).
- No unrelated dependency version was upgraded.

## CI Stage 1

`.github/workflows/build-productive.yml` added: runs the full productive pipeline
(`provision-novtk-bundle-venv.sh` → `build-productive-desktop-app.sh release`) on a clean
`macos-latest` GitHub-hosted runner, then asserts the dependency-exclusion invariants and basic
bundle structure. Triggers on push/PR to `main` and manual dispatch. **No Apple credentials, no
signing, no notarization, no certificate/keychain step of any kind** — confirmed by inspection (the
M1 gate script asserts no Apple/signing/notarization keyword appears anywhere in the workflow file).
This is Stage 1 only, per `docs/migration/BUILD-026-RELEASE-WORKFLOW-ANALYSIS.md`'s staged-adoption
recommendation — Stages 2/3 (CI-assisted/CI-built signing) remain explicitly deferred, credential-
gated, later milestones.

## Regression Evidence

- Rust: `cargo test` (all binaries), `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`
  — all clean after the `app_info()` engineering-identity bump and its accompanying regression-test
  updates (the Build-025-specific "never an earlier Build 025 milestone" guard was retired — it can
  never fire again now that `build` is permanently `"026"`, so keeping it would be a vacuous filter,
  not a regression guard — replaced with a direct stale-pair guard against the immediate predecessor,
  `025`/`M5`, matching the same pattern used for the `024`/`M2` pair before it).
- Python: full `pytest` suite, unaffected by any M1 change (M1 touched no `src/zerorodcad`/
  `src/zerorod_sidecar` source) — confirmed at the documented Build 025 baseline (380 passed, 1
  pre-existing skip).
- Frontend: unaffected by any M1 change (no frontend source touched).
- Real end-to-end pipeline: see "PyInstaller Hiddenimports Cleanup" above and the M1 gate script.

## Known Limitations

1. The macOS-26.0 minimum-version finding is a real, unresolved practical constraint — see
   "Minimum macOS Version" above. **DECISION_REQUIRED** before any real distribution.
2. CI Stage 1 has not been observed running on an actual GitHub-hosted runner within this session
   (this environment cannot trigger real GitHub Actions execution) — its correctness rests on being
   a direct translation of the exact, locally-proven-working command sequence
   (`provision-novtk-bundle-venv.sh` → `build-productive-desktop-app.sh`), not on an observed CI run.
   Should be confirmed on the first real push/PR that triggers it.
3. `scipy`/`numba`'s build-venv install versions remain unpinned (excluded from the shipped bundle
   regardless) — a `RECOMMENDED_HARDENING`, not `REQUIRED_FOR_DISTRIBUTION`, item; not closed this
   milestone.
4. All Known Limitations carried from Build 025 (`BUILD-025-COMPLETION.md`) remain unchanged — M1
   touched no product/runtime behavior.

## Legacy PySide6 / Experiments / tools/poc

Untouched. `git diff --quiet bff1944 -- src/zerorodcad_desktop/ experiments/ tools/poc/` — no
differences (verified by the M1 gate script).
