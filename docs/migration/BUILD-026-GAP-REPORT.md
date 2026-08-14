# Build 026 — Gap Report

Discovery document, synthesizing `BUILD-026-PRODUCTION-BUNDLE-AUDIT.md`,
`BUILD-026-SIGNING-NOTARIZATION-ANALYSIS.md`, `BUILD-026-RELEASE-WORKFLOW-ANALYSIS.md`, and
`BUILD-026-DEPENDENCY-AUDIT.md` into the classification the mandate requires. Nothing here was
implemented — classification only.

## First Discovery Question

> What is actually missing from the existing Build-025 release `.app` before it can reasonably be
> called a production-distribution artifact?

Answer, evidence-based: the existing `.app` is functionally complete and structurally sound (clean
bundle layout, portable relative symlinks/RPATHs, 0 excluded-dependency violations, 0 writable/debug
artifacts, consistent version fields, a working native macOS shell). What's missing is entirely in
the **distribution trust chain**: it is unsigned (ad-hoc only), has hardened runtime off, has never
been notarized, is packaged only as a raw `.app` (no `.dmg`/`.zip`), carries a placeholder-looking
bundle identifier and a stale-template minimum-OS/Carbon declaration, and — most importantly — its
own build pipeline cannot currently be reproduced from a clean machine because the CadQuery No-VTK
patch's application is undocumented local state. None of this requires a new packaging pipeline;
every gap below is a targeted addition to the existing, confirmed-single, `scripts/build-productive-
desktop-app.sh` path.

## ALREADY_PRODUCTION_READY

- Bundle structure, symlink/RPATH portability, executable permissions, 0 writable/debug artifacts
  (bundle audit).
- Icon resources, application/executable naming (bundle audit).
- Version-field internal consistency across Cargo.toml/tauri.conf.json/frontend package.json/
  Info.plist (bundle audit).
- WebView security capability boundary — exactly `["core:default", "dialog:allow-open",
  "dialog:allow-save", "core:window:allow-destroy"]`, no drift, no new capability needed for
  signing/notarization (signing analysis, packaging-pipeline audit).
- Dependency-exclusion invariants (VTK/PySide6/Qt/numba/llvmlite/scipy = 0) (dependency audit).
- `Cargo.lock`/`package-lock.json` pinning and registry-only dependency sources (dependency audit).
- Single, confirmed, non-competing productive packaging path (packaging-pipeline audit).
- Dylib dedup script's documented, evidence-based `EXPECTED_UNSAFE_EXCEPTIONS` handling
  (packaging-pipeline audit).

## REQUIRED_FOR_DISTRIBUTION

1. **CadQuery No-VTK patch clean-machine reproducibility** (dependency audit). No tracked script
   applies the patch that makes the shipped CadQuery build No-VTK; a fresh-clone build would fail or
   silently ship an unpatched, VTK-importing sidecar. Must be closed with a scripted, reproducible
   patch-application step before the packaging pipeline can be trusted for real distribution.
2. **Code signing with a real Developer ID Application certificate** (signing analysis). Currently
   ad-hoc only, `TeamIdentifier=not set`. Required for any artifact leaving this machine.
3. **Hardened runtime** (signing analysis). Currently off; required for notarization.
4. **Notarization + stapling** (signing analysis). Currently never performed; an unsigned,
   un-notarized `.app` downloaded by a real user would be rejected outright by Gatekeeper, not
   merely show a right-click override.
5. **CI coverage of the productive packaging pipeline, Stage 1 (build-only, no secrets)**
   (release-workflow analysis). Currently zero — the only existing workflow runs Python tests only.
   This is what would have caught gap #1 earlier and is the only way to have independent evidence
   the pipeline works outside this one machine.

## RECOMMENDED_HARDENING

1. Correct `LSMinimumSystemVersion` (currently `10.13`, a stale-looking template default) and remove
   or correct `LSRequiresCarbon` (Carbon is defunct; likely a Tauri/`cargo-bundle` template
   leftover) (bundle audit).
2. Decide a final, non-placeholder bundle identifier (currently `dev.zerorodcad.desktop`) (bundle
   audit).
3. Tighten the loose/unpinned Python build-venv dependencies (`casadi`, `runtype`, `scipy`, `numba`
   currently unpinned; `scipy`/`numba` are excluded from the shipped bundle regardless, but the
   build venv itself should still be reproducible) (dependency audit).
4. Add toolchain pin files (`rust-toolchain.toml`, a Node version pin) — currently only
   prose-documented (dependency audit).
5. Remove the two obsolete PyInstaller `hiddenimports` entries (`OCP.TKernel`,
   `cadquery.exporters`) with a before/after regression proof (dependency audit).
6. Adopt a `.dmg` distribution target via Tauri's native `dmg` bundle support (release-workflow
   analysis).
7. Adopt SHA-256 checksums and a release manifest for distributed artifacts (release-workflow
   analysis).
8. Explicit signing-order scripting (nested components before the outer bundle, not a bare
   `codesign --deep`) (signing analysis).

## OPTIONAL

- `.zip` as a secondary, simpler distribution artifact alongside `.dmg` (release-workflow analysis).
- CI Stage 2/3 (signing/notarization in CI) — valuable eventually, explicitly staged behind Stage 1
  and behind real Apple Developer credentials existing (release-workflow analysis).
- Custom DMG layout (background image, icon positioning) — Tauri's default is expected to be
  sufficient; no demonstrated product-value gap found (release-workflow analysis).

## DEFERRED

- Universal2 / x86_64 architecture support. No concrete distribution requirement demonstrated;
  Apple Silicon has been the sole new-Mac architecture since 2020. A separate x86_64
  `cadquery-ocp-novtk` wheel exists on PyPI (dependency-feasible) but no universal2 fat wheel does,
  and no product need currently justifies the added build/signing complexity of two architecture-
  specific artifacts (bundle audit, release-workflow analysis).
- `.pkg` installer format — no install-time script requirement exists for this app; unjustified
  added complexity (release-workflow analysis).
- Real credential acquisition, real signing, real notarization submission — explicitly out of scope
  for this discovery pass per the mandate; a later, explicitly `CREDENTIAL_GATED` milestone.
- PySide6 removal — explicitly the Post-Build-026 retirement decision, untouched here.
- Settings, Recent Files, drag & drop, file associations/Finder integration — never in Build 026's
  scope per `ROADMAP.md`; not revisited by this discovery.

## DECISION_REQUIRED

1. **Bundle identifier final value** — `dev.zerorodcad.desktop` vs. a production-shaped identifier
   (e.g. `com.zerorodcad.app` or similar reverse-DNS). Changing this after any real install breaks
   that install's update-identity continuity, so it should be decided once, deliberately (bundle
   audit).
2. **`LSMinimumSystemVersion` target value** — what minimum macOS version ZeroRodCAD should actually
   claim to support (bundle audit).
3. **Versioning strategy** — whether to adopt semantic versioning (`0.1.0` → e.g. `1.0.0`) as a
   distinct public-facing axis from the internal `app_info()` build/milestone identity pair, and at
   what point (release-workflow analysis).
4. **Architecture scope** — confirm arm64-only is acceptable for the first distributable, or state a
   concrete x86_64 requirement if one exists that this discovery pass didn't surface (bundle audit).

## Security Review Answer (restated from the signing analysis)

**Does production distribution require any new WebView capability? No.** Confirmed by direct
inspection of `desktop/src-tauri/capabilities/main-capability.json` and cross-referenced against
every proposed Build 026 gap above — none of them (signing, hardened runtime, entitlements,
notarization, DMG packaging, CI) touches the WebView-facing permission boundary. The one entitlement
candidate commonly reached for by PyInstaller-bundling apps
(`com.apple.security.cs.disable-library-validation`) is explicitly **not proposed**, pending
evidence it's actually needed after correct nested-binary signing.

## No Unauthorized Signing/Notarization Occurred

Confirmed: no `codesign` call with a real identity, no `notarytool submit`, no Keychain
modification, and no credential search/print/access was performed anywhere in this discovery pass —
verifiable by the fact that the bundle audit's own `codesign -dv` output (captured *after* this
discovery pass's inspection work) still shows `adhoc,linker-signed` / `TeamIdentifier=not set`,
unchanged from before.

## No Production Implementation Started

Confirmed: `git status --short` on the discovery branch shows only the five new documentation files
this discovery pass created — no source, test, configuration, capability, entitlement, CI, or
dependency-version change anywhere in the tracked repository.

## Discovery Gate

All items in §48 of the mandate are satisfied:

- current final app audited — bundle audit
- productive build path verified — packaging-pipeline audit
- bundle metadata audited — bundle audit
- architecture target evaluated — bundle audit, release-workflow analysis
- distribution format evaluated — release-workflow analysis
- signing topology understood — signing analysis
- hardened runtime assessed — signing analysis
- entitlements assessed — signing analysis
- notarization workflow understood — signing analysis
- credential strategy documented — signing analysis
- dependency audit completed — dependency audit
- hidden-import warnings investigated — dependency audit
- reproducibility gaps identified — dependency audit (the CadQuery-patch finding)
- clean-machine build assumptions documented — dependency audit
- release workflow proposed — release-workflow analysis
- milestone plan derived — see final discovery report
- no unauthorized signing/notarization occurred — confirmed above
- no production implementation started — confirmed above

**BUILD-026 DISCOVERY GATE: PASS**
