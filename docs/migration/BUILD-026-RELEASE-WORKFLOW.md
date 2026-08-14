# Build 026 — Release Workflow

The concrete, current release sequence for a ZeroRodCAD macOS Release Candidate — what's automated,
what's manual, and where the credential-gated boundary sits. Supersedes the proposed sequence in
`BUILD-026-RELEASE-WORKFLOW-ANALYSIS.md` (Discovery) with the sequence actually implemented and
proven in this build stream.

## Sequence

```text
clean checkout
  |
scripts/provision-portable-python.sh          (pinned URL + SHA-256, fail-fast on mismatch)
  |
scripts/provision-novtk-bundle-venv.sh         (pinned deps, explicit numpy macosx_11_0_arm64
  |                                              wheel, applies apply-cadquery-novtk-patch.sh)
scripts/build-productive-desktop-app.sh release
  |  1/5 PyInstaller onedir sidecar
  |  2/5 stage sidecar into Tauri resources
  |  3/5 tauri build --bundles app   (app only — dmg comes after dedup)
  |  4/5 hash-gated dylib dedup
  |  5/5 hdiutil DMG from the deduped .app (Applications-symlink staged)
  |
scripts/validate-build026.sh                   (the master gate — metadata, Mach-O floor,
  |                                              dependency invariants, full test suites, real
  |                                              pipeline + project roundtrip, DMG structure,
  |                                              manifest/checksums, signing-infra static checks)
  |
scripts/generate-release-manifest.sh           (flat JSON manifest + SHA256SUMS.txt, no secrets)
  |
[[ CREDENTIAL-GATED BOUNDARY — nothing below this line is authorized without real Apple
   Developer credentials and explicit, separate Project Owner authorization ]]
  |
packaging/tauri/sign_bundle.sh --identity "Developer ID Application: <Org> (<TEAMID>)"
  (nested dylibs/extensions -> sidecar executable -> main executable -> outer .app, in that
   order — never a single `codesign --deep` pass)
  |
codesign the DMG container itself (separate, additional step after DMG creation)
  |
packaging/tauri/verify_signing.sh              (codesign --verify --deep --strict, spctl -a -vv)
  |
packaging/tauri/notarize_bundle.sh --profile "<keychain-profile>"
  (notarytool submit --wait -> stapler staple -> stapler validate)
  |
regenerate the release manifest with signed=true, notarized=true, signing_identity, and the
signed/notarized artifact's own checksums (expected to differ from the unsigned fingerprint —
see "Artifact Identity" below, this is normal, not a reproducibility break)
  |
final signed-distribution Human Validation (a real download-and-launch cycle, not a local build)
  |
publish
```

## Artifact Identity

Three distinct identities are tracked, deliberately not conflated:

- **Unsigned `.app` content fingerprint**: `scripts/generate-release-manifest.sh`'s own
  methodology (sorted relative paths, per-file SHA-256, symlink targets, aggregate SHA-256) —
  reproducible build-to-build given identical source and dependency versions.
- **Signed artifact hash**: computed after real Developer ID signing. Expected to differ from the
  unsigned fingerprint every signing run, even from byte-identical input — a code signature embeds
  a cryptographic timestamp by design. Not a reproducibility failure; verify what was signed, not
  that signing is byte-deterministic.
- **Notarized release hash**: computed after `stapler staple`. Also expected to differ run-to-run
  (embeds a notarization ticket tied to a specific submission).

## Naming Convention

```text
ZeroRodCAD-<public-version>-macOS-arm64.dmg
```

e.g. `ZeroRodCAD-0.1.0-macOS-arm64.dmg` (this build's actual artifact name). Deliberately separate
axes, never conflated: the filename carries only the public semantic version and architecture; the
internal engineering identity (`app_info()`'s `build`/`milestone` pair, currently `026`/`Final`) is
a distinct concern, visible in the app's own Diagnostics view and the release manifest's
`engineering_build` field, not in the distributed filename.

## Dependency Audit (final)

See `docs/migration/BUILD-026-COMPLETION.md`'s "Dependency / Build Pinning" table for the full,
current pin-status inventory (Python/PyInstaller/CadQuery/cadquery-ocp-novtk/numpy/casadi/runtype
all exact-pinned; Rust/Node toolchain-pinned; Tauri/Three.js lockfile-pinned; scipy/numba build-venv
versions and legacy-app PySide6 justified as still-floating).

## Security

No new WebView capability, no new entitlement, no new network surface introduced by this workflow.
Notarization submission is the only network interaction beyond dependency downloads, and it is
credential-gated and not yet performed. See `docs/migration/BUILD-026-COMPLETION.md`'s "Security"
section for the full current-state re-verification.

## Credential-Gated Final Release Step

Everything below the boundary marked above in "Sequence" requires real Apple Developer credentials
and explicit, separate Project Owner authorization — not performed by any Build 026 work to date.
