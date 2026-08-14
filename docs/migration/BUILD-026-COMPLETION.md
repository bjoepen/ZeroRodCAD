# Build 026 — Production Packaging & macOS Integration — Completion Record

## Status

**FINALIZATION ENGINEERING COMPLETE** for the non-credential-gated Release Candidate. Real
Developer ID signing, notarization, and stapling remain explicitly deferred, credential-gated, and
NOT performed by this build. Master gate: `scripts/validate-build026.sh` →
`BUILD-026 CONSISTENCY GATE: PASS`.

## Purpose

Build 026 turns the already-validated ZeroRodCAD Tauri application (Build 022–025) into a hardened,
reproducible, distributable macOS artifact — without redesigning the product architecture or adding
unrelated features. This build proceeded as one controlled finalization stream (Discovery → M1
production-bundle hardening → M1.1 portable-Python research → this finalization), per the Project
Owner's explicit instruction not to further decompose Build 026 into additional milestones.

## Baseline

- Build 022–025: COMPLETE / PASS (own completion records).
- Discovery (`244dddd`): Gate PASS — audited the Build 025 final `.app`, proposed a milestone plan.
- M1 (`b3f8b32`): Engineering PASS, Human Validation PASS — closed the CadQuery No-VTK clean-machine
  reproducibility gap, corrected bundle metadata, removed obsolete PyInstaller hiddenimports, added
  CI Stage 1. Measured the productive bundle's genuine macOS floor at 26.0 (Homebrew-Python-driven)
  and flagged it `DECISION_REQUIRED` rather than accepting it as final.
- M1.1 (`4b3d42c`): Research Gate PASS — proved a portable, pinned CPython 3.13
  (`astral-sh/python-build-standalone`) plus an explicitly-selected numpy wheel brings the real,
  measured, full-bundle Mach-O floor down to **11.1** (OpenCASCADE-bound), with the Rust/Tauri
  binary's own floor traced to `tauri.conf.json`'s `bundle.macOS.minimumSystemVersion`.
- Finalization (this record): branched from `4b3d42c` as `feature/build026-finalization`.

## Accepted Decisions

| Decision | Value |
|---|---|
| Architecture | ARM64 only |
| Minimum macOS | **11.1** — empirically proven full productive bundle floor; OpenCASCADE (`cadquery-ocp-novtk`) is the binding component |
| Public version | `0.1.0` |
| Engineering identity | Build `026` / `Final` |
| Bundle identifier | `de.zerorodcad.desktop` |
| Primary distribution artifact | DMG |
| Productive Python | pinned `astral-sh/python-build-standalone` CPython 3.13.15 (release `20260807`) |
| numpy | explicit `macosx_11_0_arm64` wheel (PyPI's default-selected `macosx_14_0_arm64` wheel avoided) |
| Real signing/notarization | NOT authorized without explicit credentials/approval |

## What This Build Delivers

```text
Reproducible portable Python provisioning  -> scripts/provision-portable-python.sh
                                               (pinned URL + SHA-256, no Homebrew dependency)
Automated No-VTK patching                  -> scripts/apply-cadquery-novtk-patch.sh (unchanged since M1)
Clean productive build                     -> scripts/build-productive-desktop-app.sh
Correct metadata                            -> identifier, version, minimum macOS 11.1, LSRequiresCarbon
Clean PyInstaller config                    -> 0 hidden-import warnings
Final dependency audit                      -> VTK/PySide6/Qt/numba/llvmlite/scipy = 0
DMG generation                              -> ZeroRodCAD-0.1.0-macOS-arm64.dmg
Release naming / checksums / manifest       -> scripts/generate-release-manifest.sh
Signing/notarization infrastructure         -> packaging/tauri/{sign,notarize,verify}_*.sh (no real credentials)
Final release validation                    -> scripts/validate-build026.sh
Final Human Validation artifact             -> ZeroRodCAD-Build026-Final.app
```

## Portable Python Integration

Replaces the previous Homebrew-Python dependency for the productive packaging environment.
`scripts/provision-portable-python.sh` downloads a single pinned release asset
(`cpython-3.13.15+20260807-aarch64-apple-darwin-install_only.tar.gz`, SHA-256
`ebcf53fe921c356ad2eecfcea370cb744e7bd96fdef41a53e1e8f32a15c6dfeb`), verifies the checksum, the
archive layout, and the installed Python version — all fail-fast — before use. Idempotent (skips
re-download/re-extraction if already correctly provisioned).
`scripts/provision-novtk-bundle-venv.sh` uses this portable Python exclusively (no `PATH`
`python3.13` dependency, no Homebrew reference anywhere), and explicitly force-installs numpy's
`macosx_11_0_arm64`-tagged wheel (downloaded and installed by local file path, since `pip install
--platform` is refused for a live-environment install) rather than trusting pip's default
platform-tag resolution, which would otherwise silently select the `macosx_14_0_arm64` variant on
this build machine. `.github/workflows/build-productive.yml` (CI Stage 1) uses the identical
provisioning script — no separate CI-only Python path exists.

## No-VTK Reproducibility

The M1 mechanism (`scripts/apply-cadquery-novtk-patch.sh`) is unchanged and reused verbatim against
the portable-Python venv — proven Python-source-agnostic in M1.1's research pass and re-confirmed
here via a real, clean provisioning run.

## Metadata

Verified against the actual compiled `Contents/Info.plist`, not source configuration alone:

| Field | Value |
|---|---|
| `CFBundleIdentifier` | `de.zerorodcad.desktop` |
| `CFBundleShortVersionString` / `CFBundleVersion` | `0.1.0` |
| `LSMinimumSystemVersion` | `11.1` |
| `LSRequiresCarbon` | `false` |

## Mach-O Deployment-Target Floor

A full scan of every Mach-O file in the final bundle (110 files):

| `minos` | File count |
|---|---|
| 11.0 | 58 |
| 11.1 | 52 (all OpenCASCADE `libTK*.dylib` / `OCP.cpython-313-darwin.so`) |

**Maximum: 11.1.** No file exceeds this. OpenCASCADE is the binding constraint — no lower
alternative exists for the currently-pinned `cadquery-ocp-novtk==7.9.3.1.1`, and no product
justification exists to chase it further.

A second, independent finding from this build stream: Tauri's own bundler derives the
`MACOSX_DEPLOYMENT_TARGET` it passes to `cargo build` from `tauri.conf.json`'s
`bundle.macOS.minimumSystemVersion` — not from the shell environment. Both the Python-side and
Rust-side floors are therefore controlled from the same, single source of truth.

## PyInstaller Hardening

`OCP.TKernel` and `cadquery.exporters` (both confirmed `OBSOLETE_HIDDEN_IMPORT` — see
`BUILD-026-DEPENDENCY-AUDIT.md`) were removed from `packaging/tauri/sidecar-onedir.spec`'s
`hiddenimports` list in M1 and remain removed. **0** `Hidden import ... not found` warnings in the
final rebuild (previously 2 per build). Regression-proven via a real end-to-end pipeline exercise
(preview, alternate preview, report, project save/open with differing mesh bounds, STL/STEP export,
shutdown) against the freshly rebuilt sidecar.

## Dependency / Build Pinning

| Component | Pin status |
|---|---|
| Python | exact — pinned tarball, SHA-256-verified |
| PyInstaller | exact — `6.22.0` |
| CadQuery | exact — `2.8.0` |
| cadquery-ocp-novtk | exact — `7.9.3.1.1` |
| numpy | exact — `2.4.6`, explicit `macosx_11_0_arm64` wheel |
| casadi | exact — `3.7.2` |
| runtype | exact — `0.5.3` |
| Rust | toolchain-pinned — `rust-toolchain.toml`, `1.97.1` |
| Node | toolchain-pinned — `.nvmrc`, `24` |
| Tauri | lockfile-pinned — `Cargo.lock`, `2.11.5` |
| Three.js | lockfile-pinned — `package-lock.json` |
| scipy/numba (build-venv only, excluded from shipped bundle) | still floating — justified: never reach the shipped artifact, pinning would add churn with no reproducibility benefit to the *product* |
| PySide6 (legacy-app-only, shared venv) | still range-pinned (`>=6.7,<7`) — out of the Tauri productive path's scope; unrelated-upgrade avoidance |

## CI Stage 1

`.github/workflows/build-productive.yml` builds the full productive `.app` + DMG on a clean
`macos-latest` runner using the identical portable-Python provisioning mechanism as local
development — no Homebrew, no `actions/setup-python`, no Apple credentials, no signing, no
notarization. Adds a Mach-O deployment-target floor check (`<= 11.1`) alongside the existing
dependency-exclusion invariants. **Not observed running on a real hosted runner** in this
development environment (which cannot trigger real GitHub Actions execution) — it is a direct,
structural translation of the exact command sequence proven locally, not independently CI-verified.

## DMG

`scripts/build-productive-desktop-app.sh` was corrected to build the DMG as an explicit final step,
*after* the dylib-dedup step — the naive approach (Tauri's single `tauri build` call producing both
`.app` and `.dmg` bundle targets together) was found to package the DMG *before* dedup ran, shipping
~112 MiB of avoidable duplicate dylibs. The DMG is now built via `hdiutil` from the already-deduped
`.app`, staged with an `Applications` symlink for the standard drag-to-install convention (no
decorative custom layout). Verified via a real mount/copy/launch cycle: DMG opens, shows
`ZeroRodCAD.app` + an `Applications` alias, and a copy dragged to a simulated Applications folder
launches correctly.

## Release Manifest & Checksums

`scripts/generate-release-manifest.sh` produces a flat, secret-free JSON manifest
(`build/reports/build026-release/release-manifest.json`) and a `SHA256SUMS.txt`, covering: product,
public version, engineering build, git commit, architecture, bundle identifier, minimum macOS,
frontend asset identity, an unsigned `.app` content fingerprint (Build 025's own sorted-path/
per-file-SHA-256/symlink-target methodology), and the DMG's SHA-256. `signed`/`notarized` fields are
explicitly `false`/`null` — this is an honest unsigned manifest, not a placeholder pretending
otherwise.

## Signing/Notarization Preparation (infrastructure only — no real credentials)

- `packaging/tauri/sign_bundle.sh`: discovers every nested Mach-O component and signs in the correct
  order (nested dylibs/extensions → sidecar executable → main executable → outer bundle) — never a
  single `codesign --deep` pass. Defaults to `--dry-run` (prints the exact commands it would run);
  real signing requires an explicit `--identity` naming a certificate that must already exist in the
  local Keychain. No entitlements file was fabricated — evidence-based conclusion (M1's signing
  analysis) is that none is currently required; `--entitlements` is omitted from every invocation
  rather than pointed at a speculative file.
- `packaging/tauri/notarize_bundle.sh`: documents and scripts the `notarytool submit --wait` →
  `stapler staple` → `stapler validate` workflow. Defaults to dry-run (prints the commands); real
  submission requires an explicit `--profile` naming a `notarytool`-managed Keychain profile created
  once, interactively, outside this script.
- `packaging/tauri/verify_signing.sh`: read-only `codesign`/`spctl`/entitlements/quarantine
  inspection, safe against any bundle (signed or not).

All three scripts were exercised in dry-run mode against the real final artifacts as part of this
build's own validation — structurally correct, no credential referenced, no signing performed.

## Regression

Full suites: Python (`pytest` — 380 passed, 1 pre-existing skip, unchanged from every prior Build
025/026 measurement), Rust (`cargo test`/`fmt`/`clippy` — 60 passed, all clean, including the new
`app_info_never_reports_a_stale_026_m1_pair` regression guard), Frontend (`vitest`/`tsc`/production
build — 370 passed; one test — `mesh.realpayload.test.ts`, which spawns the real sidecar binary —
shows a reproducible timeout flake under this machine's sustained concurrent build load and passes
cleanly every time it is re-run in isolation, confirmed multiple times across this build stream; not
a source regression).

Real end-to-end pipeline against the freshly built productive sidecar: `status`, `preview` (defaults
+ alternate), `report`, `project_save`→`project_open` roundtrip (value preserved), a second
`preview` after reopen with **differing mesh bounds proven directly** (not JSON equality — X extent
scales from ±19mm to ±30mm matching `body_width` 38→60mm), `export` ×2 (STL/STEP/report, both valid
and content-correct), an invalid-parameter export correctly rejected with process stability preserved
afterward, clean `shutdown`. Real packaged `.app` launch/quit (native close guard) and a real
DMG-mount → drag-to-Applications-simulation → launch → quit cycle, both ending in **0 orphan
processes**.

## Dependency Invariants

VTK = 0, PySide6 = 0, Qt = 0, numba = 0, llvmlite = 0, scipy = 0 — confirmed against the actual final
`.app`, correctly excluding two established filename false positives: `cadquery_ocp_novtk` (substring
match) and `libscipy_openblas64_.dylib` (numpy's own vendored BLAS backend, shared with the SciPy
project's build infrastructure — not the scipy package; verified no real `scipy` package/dist-info
present anywhere in the bundle).

## Security

Re-verified, 0 deviations from Build 025: WebView shell — NO. WebView broad filesystem — NO. WebView
process — NO. Capabilities — unchanged, exactly `["core:default", "dialog:allow-open",
"dialog:allow-save", "core:window:allow-destroy"]`. IPC — private stdin/stdout. CSP — unchanged,
restrictive. Remote runtime services — NONE. Build-time network — only pinned-artifact downloads
(the portable Python tarball); the future notarization submission is the only other network
interaction this pipeline will ever perform, and it remains credential-gated and unperformed.

## Performance

No regression found. Bundle size grew from Build 025's 287 MiB to 310 MiB (+~8%) — fully explained by
`python-build-standalone`'s more statically-linked `libpython3.13.dylib` (a single 17 MiB file)
versus Homebrew's more modular, multi-file `Python.framework` split; not a functional or
runtime-performance concern. Warm preview timing remained consistent with the established
~0.12–0.2 s baseline across every real pipeline exercise run in this build stream.

## Known Limitations

1. This CI workflow has not been observed executing on a real hosted GitHub Actions runner — see "CI
   Stage 1" above.
2. `mesh.realpayload.test.ts`'s load-induced timeout flake is documented, not eliminated (raising its
   internal timeout would be a reasonable follow-up, not attempted here as an unrelated improvement).
3. `scipy`/`numba` build-venv install versions and legacy-app-only `PySide6`/`Cargo` dependency
   ranges remain floating — justified, not a reproducibility gap for the shipped Tauri artifact.
4. All Known Limitations carried from Build 025 (`BUILD-025-COMPLETION.md`) remain unchanged — no
   product/runtime behavior was touched by Build 026.

## Credential-Gated Final Release Step

Explicitly NOT performed by this build, requires real Apple Developer credentials and separate
Project Owner authorization:

- Real Developer ID Application signing (`packaging/tauri/sign_bundle.sh --identity "..."`)
- Real Gatekeeper assessment of an actually-downloaded, quarantined signed artifact
- Real `notarytool submit` notarization
- Stapling
- A final signed/notarized artifact checksum
- Final signed-distribution Human Validation

## Legacy PySide6 / Experiments / tools/poc

Untouched throughout Build 026 (Discovery, M1, M1.1, and this finalization) — verified by
`git diff --quiet bff1944 -- src/zerorodcad_desktop/ experiments/ tools/poc/` in every gate run.

## Next

Await Project Owner Human Validation of `ZeroRodCAD-Build026-Final.app` and
`ZeroRodCAD-0.1.0-macOS-arm64.dmg`. If accepted, the Credential-Gated Final Release Step above is the
only remaining work before a real public release — no further product/architecture changes, no
further milestone decomposition.
