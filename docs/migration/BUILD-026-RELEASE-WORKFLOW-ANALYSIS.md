# Build 026 — Release Workflow Analysis

Discovery document. No release, package, signing, versioning, or CI change was made to produce this
analysis — it proposes a sequence for a later, explicitly approved implementation milestone.

## Current Build Path (confirmed from source)

```text
scripts/build-productive-desktop-app.sh release
    -> pyinstaller packaging/tauri/sidecar-onedir.spec   (onedir sidecar, no onefile)
    -> cp -R sidecar into desktop/src-tauri/resources/zerorod-engine-onedir (symlinks preserved)
    -> tauri build (release)
    -> packaging/tauri/dedup_bundle_dylibs.py             (hash-gated symlink restoration)
    -> ZeroRodCAD.app
```

Single authoritative productive path, confirmed by the packaging-pipeline audit: no competing
Tauri packaging script exists. `tauri.conf.json`'s `bundle.targets = ["app"]` — Tauri currently
produces only the raw `.app`, nothing further (no `.dmg`, no `.zip`).

## Distribution Artifact Format

| Format | User experience | Gatekeeper | Signing/notarization | Complexity | Tauri support |
|---|---|---|---|---|---|
| `.app` (raw, e.g. zipped for transfer) | Drag-and-drop or double-click after unzip; no visual install ceremony | Same underlying assessment as any format — quarantine attribute travels with whatever container delivered it | Fully compatible — notarization staples to the `.app` itself | Lowest | Native (`bundle.targets: ["app"]`, already in place) |
| `.zip` | Standard "download → double-click to expand → drag to Applications (manual)" | Quarantine attribute set on the zip by the browser, inherited by the expanded `.app` | Fully compatible; smallest artifact, fastest notarization submission (no HFS+/APFS image parsing) | Low | Native Tauri target (`bundle.targets` can include `"app"` — Tauri wraps as zip during CI artifact upload, or a plain `zip -r` post-build) |
| `.dmg` | Familiar macOS convention: mount, drag app icon onto an `Applications` shortcut, eject | Same quarantine/notarization model as zip, plus the DMG itself can carry its own notarization ticket | Fully compatible; Tauri has first-class `dmg` bundle target support | Medium (background image/icon layout optional) | Native Tauri target (`bundle.targets: ["app", "dmg"]`) |
| `.pkg` | Guided installer wizard; can run install scripts/postinstall hooks | Same signing/notarization requirements, plus a separate **Installer** certificate type (distinct from Developer ID Application) | More moving parts: needs `productbuild`/`pkgbuild`, a second certificate type | Highest | Not a first-class Tauri bundle target |

**Recommendation**: `.dmg` as the primary distributable, matching the familiar "drag ZeroRodCAD.app
into Applications" macOS convention the Project Owner and any future user will already expect, with
Tauri's native `dmg` target doing the work — no custom DMG tooling needed unless a specific UX gap
is found (see DMG Audit below). `.zip` is worth keeping as a secondary, simpler artifact for
CI-internal transfer or a fast pre-release smoke-test channel (smaller, faster to notarize, no
mount/eject ceremony for a Project-Owner-only test download). `.pkg` is **not recommended** — this
app has no install-time script requirement (no LaunchAgent registration, no privileged
directory writes, no post-install configuration step), so a `.pkg`'s extra complexity and second
certificate type buys nothing.

## DMG Audit

- Tauri's built-in DMG bundling (`bundle.targets: ["app", "dmg"]` in `tauri.conf.json`) is expected
  to be sufficient: it already produces a standard drag-to-Applications layout with the app icon and
  an `Applications` symlink. No custom DMG layout (background image, icon positioning XML) is known
  to be necessary for this product — it would be decorative packaging work the mandate explicitly
  discourages without a demonstrated product-value reason.
- Signing/notarization order for a DMG: sign the fully-assembled, hardened-runtime `.app` first,
  build the DMG around the *already-signed* app, then notarize the DMG itself (notarizing the
  container is what staples the ticket users' Gatekeeper checks against on mount) — DMG-level
  signing (`codesign` on the `.dmg` file) is a separate, additional step after DMG creation, not a
  substitute for signing the inner `.app`.
- Reproducibility: DMG creation (UDIF disk image format) embeds a creation timestamp and, depending
  on tooling, can have non-deterministic block ordering — the DMG's own hash is **not** expected to
  be reproducible build-to-build even from byte-identical app content. This is normal and expected;
  the artifact-identity strategy below accounts for it by hashing the inner `.app` payload
  separately from the outer container.

## Signing Discovery — recap

See `BUILD-026-SIGNING-NOTARIZATION-ANALYSIS.md` for the full topology, hardened-runtime
assessment, entitlements proposal, and credential strategy. Current state: ad-hoc only, no
Developer ID, hardened runtime off.

## Reproducibility Impact

Build 025 established a deterministic **unsigned** bundle fingerprint methodology (sorted relative
paths + per-file SHA-256 + symlink targets, aggregated). Signing and notarization change bytes in
ways that must be tracked as **distinct identities**, not silently conflated:

- **UNSIGNED BUILD FINGERPRINT**: the existing Build 025 methodology, computed against the raw
  `.app` immediately after `dedup_bundle_dylibs.py` and before any `codesign` call. Reproducible
  build-to-build *given identical source and identical dependency versions* (see the dependency
  audit for where that assumption currently breaks).
- **SIGNED ARTIFACT HASH**: computed *after* real Developer ID signing with `--options runtime
  --timestamp`. This will **not** match the unsigned fingerprint — code signatures embed a
  cryptographic timestamp (via Apple's timestamp authority) that is different on every signing
  run even from byte-identical input, by design (this is what lets Gatekeeper trust the signature
  after the certificate itself later expires). Do not expect byte-for-byte reproducibility here;
  the invariant to preserve instead is "the *signed, pre-signature* content hashes match the known
  unsigned fingerprint" (i.e. verify what was signed, not that signing is deterministic).
- **NOTARIZED RELEASE HASH**: computed after `stapler staple`. Also non-reproducible run-to-run for
  the same reason (embeds Apple's notarization ticket, itself tied to a specific submission).

**Proposed practice**: keep computing and recording the unsigned fingerprint at build time
(continuing Build 025's discipline unchanged) as the true content-identity proof, and record the
signed/notarized hashes as *this specific release's* checksums (for download integrity
verification) — not as a reproducibility claim. This distinction should be stated explicitly in
every future release's manifest so nobody mistakes a changed signed-artifact hash for a content
regression.

## Artifact Identity Strategy

Proposed release metadata (no secrets), extending Build 025's existing discipline:

```text
product: ZeroRodCAD
version: <semantic version, see below>
git_commit: <full SHA>
architecture: arm64
bundle_identifier: <decided value, see bundle audit>
unsigned_fingerprint: <sha256, Build-025-methodology>
signed_sha256: <sha256 of the signed .app/.dmg/.zip as actually distributed>
distribution_sha256: <sha256 of the final distributed container, e.g. the .dmg file itself>
signing_identity: <"Developer ID Application: <Org> (<TEAMID>)" — identity string only, never a
                    certificate or password>
notarization_status: <accepted | not-notarized, plus submission ID if accepted>
build_timestamp: <UTC ISO 8601, only if the release process records one>
```

No secret is ever part of this manifest — signing identity is a public string (it's literally what
`codesign -dv` already reveals on any signed binary), not a credential.

## Versioning Strategy

Current state: `0.1.0` (Cargo.toml/tauri.conf.json/frontend package.json, all consistent) has never
moved since Build 022; `app_info()`'s `build="025"`/`milestone="M5"` is a **separate, deliberate
engineering-identity axis** tracking internal migration progress, not a public release number.

**Proposed reconciliation** (a proposal for Build 026's own milestone to decide and implement, not
decided here): adopt semantic versioning for the public product version, independent of the
internal build/milestone counters, e.g. `0.1.0` → `1.0.0` at the point Build 026 produces the first
real signed/notarized distributable (marking "first thing meant to leave this machine"), with
`app_info()`'s build/milestone pair continuing to serve its existing internal-engineering-identity
purpose unchanged. Keep the two pairs **visibly distinct** in the Diagnostics view and any release
manifest (e.g. "Version 1.0.0 (Build 026)") rather than trying to collapse them into one number —
they answer different questions ("what can an end user expect" vs. "which internal milestone
shipped this"). This is a recommendation for Project Owner decision, not implemented here.

## Release Naming

Proposed deterministic convention (not implemented):

```text
ZeroRodCAD-<version>-macOS-arm64.dmg
ZeroRodCAD-<version>-macOS-arm64.zip
```

e.g. `ZeroRodCAD-1.0.0-macOS-arm64.dmg`. Keeps engineering build number, product semantic version,
and distribution filename as three separate, clearly-labeled concerns (per the mandate's own
instruction) — the filename carries only the public version and architecture, never the internal
Build/Milestone pair.

## Checksums

Recommend `SHA-256` (matching Build 025's existing convention, no new hash algorithm introduced) for
every distributed file: the `.dmg`/`.zip` itself, and optionally the inner `.app`'s unsigned
fingerprint for cross-reference. Publish alongside the release, e.g. as a plain `.sha256` sidecar
file — not implemented here.

## Release Manifest

A simple machine-readable manifest (JSON, matching the artifact-identity fields above) is
recommended — useful for a future automated release-notes/changelog step and for the Project Owner
to verify a specific download against its expected identity without re-deriving it by hand. No
release-management framework beyond this flat file is recommended; the mandate's own instruction
against over-building applies directly here.

## Proposed Release Sequence (derived from the actual bundle, not assumed)

```text
clean checkout
  |
dependency verification (Cargo.lock --locked, npm ci, Python 3.13 pin check — all
  already-enforced or enforceable per the dependency audit; CadQuery-patch reproducibility
  gap must be closed first, see BUILD-026-DEPENDENCY-AUDIT.md)
  |
sidecar build (PyInstaller onedir, current script)
  |
Tauri release build
  |
dylib dedup (current script)
  |
bundle validation (dependency-exclusion invariants, structure checks — extending Build 025's
  existing checks, not a new tool)
  |
sign nested components (dylibs/extensions -> sidecar executable -> main executable, in that
  order — see signing-topology analysis)
  |
sign outer .app bundle (last, after every nested component)
  |
codesign verify (--verify --deep --strict, and spctl -a -vv) on the signed .app
  |
package DMG (Tauri native dmg target, around the already-signed .app)
  |
sign DMG container
  |
notarize (notarytool submit --wait, on the signed DMG)
  |
staple (stapler staple, on the DMG)
  |
final validation (spctl -a -vv --type execute, stapler validate, plus the existing Build-025-style
  packaged-app smoke test: launch, sidecar reachable, initial model, shutdown, 0 orphans)
  |
checksums (SHA-256 of the final .dmg, plus the recorded unsigned .app fingerprint)
  |
release manifest
```

This order is derived directly from what the current bundle actually contains (confirmed nested
Mach-O topology, confirmed single packaging path, confirmed DMG target availability in Tauri) —
not assumed from generic guidance. It is a **proposal for a later, explicitly authorized
implementation milestone**; nothing in this sequence was executed during this discovery pass.

## CI Recommendation

Current CI (`.github/workflows/tests.yml`) runs Python `pytest`/`ruff` on `macos-latest` plus a
`pre-commit` job on `ubuntu-latest` — it does **not** build the Rust/Tauri app, run Rust or frontend
tests, or exercise the productive packaging pipeline at all. This means there is currently zero
independent CI evidence that `scripts/build-productive-desktop-app.sh` reproduces cleanly outside
this one local machine — directly corroborating the clean-machine reproducibility gap found in the
dependency audit.

**Staged adoption recommended** (not implemented):

1. **Stage 1 — CI build, no signing**: add a CI job that runs the full productive pipeline (sidecar
   + Tauri release build + dedup) on a clean `macos-latest` runner and asserts the dependency-
   exclusion invariants and bundle-structure checks, with no secrets involved at all. This alone
   would immediately either confirm or falsify clean-machine reproducibility — currently unknown.
2. **Stage 2 — CI-assisted signing**, only after Stage 1 is solid and Apple Developer credentials
   exist: import the signing certificate into a per-run temporary Keychain from encrypted GitHub
   Actions secrets (see credential strategy in the signing analysis), sign, and upload the signed,
   unnotarized artifact for manual inspection before any real release.
3. **Stage 3 — CI-built releases**, only after Stage 2 has been manually verified safe on real
   tagged releases: full sign + notarize + staple + publish, triggered on a version tag, not on
   every push.

Do not skip to Stage 3. Assessed factors: secrets (Stage 2+ only, scoped narrowly per the
credential strategy), Apple certificate installation (ephemeral, per-run, never persisted to the
runner disk), notarization credentials (App Store Connect API key preferred over Apple-ID/password
for CI, per the signing analysis), artifact retention (GitHub Actions' standard artifact retention
is sufficient; no new infrastructure needed), reproducibility (Stage 1 is what actually tests this),
trust model (a compromised CI secret at Stage 2+ could sign malicious code with the project's real
Developer ID — scope runner access and secret exposure accordingly, e.g. environment-protected
secrets requiring manual approval for release-tag-triggered runs).

## Upgrade / Replacement Behavior

No persisted application settings/state exists outside `.zerorod` project files (confirmed: Build
025's completion record and the Diagnostics view describe only read-only engine/sidecar status, no
app-level preferences store). Replacing an older `ZeroRodCAD.app` with a newer one is therefore
expected to be **stateless at the app level** — a user's `.zerorod` project files on disk are
untouched by an app replacement (they're independent files, not app-bundle content), and there is
no settings migration concern because there are no settings yet. No updater was designed or
implied by this observation — none exists, none is proposed here.

## Project File Compatibility

**Project format unchanged.** No finding in this discovery pass gives any reason for production
packaging/signing work to touch `.zerorod` (`src/zerorodcad/project.py`) — signing operates on the
already-built `.app` bundle, entirely downstream of and unrelated to the project file format. This
is stated per the mandate's explicit instruction, not left implicit.

## Release Validation Matrix (future, proposed)

Extends Build 025's existing final-artifact validation discipline with the new signing/notarization
axis:

```text
clean build
bundle structure
dependency invariants (VTK/PySide6/Qt/numba/llvmlite/scipy = 0)
codesign verification (--verify --deep --strict)
Gatekeeper assessment (spctl -a -vv --type execute)
notarization assessment (stapler validate)
stapling assessment
launch
automatic initial model
project save/open
report
STL/STEP export
native menus
Cmd+Q / red-close guard
shutdown, 0 orphan processes
```

Human Validation required for the final distributable artifact, same discipline as every prior
build.
