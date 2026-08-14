# Build 026 — Signing & Notarization Analysis

Discovery document. No signing, notarization, Keychain modification, or credential access was
performed to produce this analysis. Current-state findings are cited from
`BUILD-026-PRODUCTION-BUNDLE-AUDIT.md`; this document covers what real signing/notarization would
require and how it can be prepared for without secrets.

## Current State (recap)

- Ad-hoc, linker-signed only (`flags=0x20002(adhoc,linker-signed)`), `TeamIdentifier=not set`,
  `Sealed Resources=none`. Not a Developer ID signature.
- Hardened runtime: off.
- No entitlements embedded.
- No quarantine attribute on the locally-built copy — not representative of a downloaded release
  (see "Download/Quarantine Simulation" below).
- `spctl -a -vv` cannot even fully assess the bundle (`code has no resources but signature
  indicates they must be present`).

## Signing Topology

The `.app` contains, per the bundle audit:

- 1 Rust/Tauri main executable (`Contents/MacOS/zerorod-desktop`)
- 1 Python sidecar executable (`Contents/Resources/zerorod-engine-onedir/zerorod-engine`)
- Python.framework (interpreter + stdlib, 7 framework-related files)
- 156 `.dylib` files (100 OpenCASCADE `libTK*`, 2 `libcasadi*`, plus numpy/Python-related), 77 of
  which are symlinks into `_internal/OCP/.dylibs/` and `.dylibs/` real targets
- 77 `.so` extension modules (CadQuery/OCP/numpy compiled Python extensions)

**Correct topology**: `codesign` must sign every nested Mach-O binary *individually, from the
inside out*, before signing the outer `.app` bundle — this is what real Developer ID signing
requires regardless of tooling (`codesign --deep` is a shortcut that signs nested code with the
*same* flags/entitlements as the outer bundle in one pass, which is adequate for many apps but is
explicitly flagged in Apple's own guidance as unsuitable when nested binaries have different
entitlement needs or when reproducibility/auditability of the signing step matters). Given:

- The OpenCASCADE dylibs and CadQuery/OCP `.so` extensions are third-party binary dependencies with
  no entitlement needs of their own (no elevated privilege, no exec, no filesystem beyond what
  Python's `pip`-installed native extensions already do) — they need a valid Developer ID
  **code** signature (so the signed outer bundle's Gatekeeper assessment doesn't fail on an
  unsigned nested binary) but not a distinct entitlements set.
- `zerorod-engine` (the sidecar) is spawned as a subprocess by the Rust `zerorod-desktop` binary via
  `tauri-plugin-shell` — it needs its own valid signature (subprocess execution under hardened
  runtime enforces the parent's protections partly through the child's own signature validity) but,
  like the dylibs, no bespoke entitlement.
- `zerorod-desktop` (the outer/main executable) is the only binary that needs the **product-level**
  entitlements (see below) and must be signed **last**, after every nested component, so its seal
  covers the final, fully-signed nested tree.

**Recommended approach for Build 026's eventual signing milestone**: an explicit, scripted signing
order (sidecar dylibs/extensions → sidecar executable → main executable → outer bundle) via
individual `codesign --sign "<Developer ID>" --options runtime --timestamp <path>` invocations in a
loop over `find`-discovered nested Mach-O files, *not* a single `codesign --deep` call — so the
process is auditable, reproducible, and each binary's actual entitlement needs stay explicit rather
than uniformly inherited. This is a preparation recommendation, not implemented here.

## Hardened Runtime

Currently off (ad-hoc signatures cannot carry it). Enabling it (`--options runtime` at sign time)
is required for notarization (Apple rejects non-hardened-runtime submissions as of the current
notarization policy referenced in `docs/adr/ADR-022-001` and industry-standard practice). Assessed
impact per component:

- **Tauri/WebView**: Tauri v2 apps are hardened-runtime-compatible by design (this is the standard,
  documented configuration for shipped Tauri macOS apps) — no known blocker.
- **PyInstaller Python sidecar**: hardened runtime restricts unsigned/ad-hoc code loading and
  certain runtime behaviors (e.g. DYLD environment variable injection, unsigned executable memory).
  A PyInstaller onedir bundle with all its `.dylib`/`.so` payload properly signed does not itself
  need library validation disabled — it only becomes a problem if any nested binary is *unsigned* at
  runtime-load time, which is exactly why the signing topology above (sign every nested binary
  first) matters.
- **CadQuery/OCP native extensions**: same as above — once each `.so`/`.dylib` in the OCP payload
  carries a valid signature, hardened runtime does not need to know they're "different"; there is no
  known CadQuery/OCP runtime behavior (e.g. JIT code generation, unsigned dlopen) that would require
  an exception. `numba`/`llvmlite` — the two dependencies in the CadQuery ecosystem most associated
  with JIT-compiled unsigned memory pages — are already excluded from the bundle (Build 022–025
  packaging decision), which removes the most likely source of a real hardened-runtime conflict.
- **Subprocess launch (`tauri-plugin-shell` spawning `zerorod-engine`)**: hardened runtime does not
  block a parent app from spawning a *properly signed* child process; it blocks spawning of
  unsigned/tampered code. As long as the sidecar executable itself is correctly signed (see
  topology above), this is not expected to require an entitlement.
- **stdin/stdout IPC**: no sandboxing or hardened-runtime restriction applies to a private,
  same-process-tree stdin/stdout pipe; this channel is unaffected.

No entitlement is currently known to be required beyond the ones below. In particular,
**`com.apple.security.cs.disable-library-validation`** — the broad escape hatch some PyInstaller
apps reach for — is **not recommended** unless a real load failure is observed after all nested
binaries are correctly signed; per the mandate's own least-privilege instruction, this analysis
does not propose it speculatively.

## Entitlements Audit

None currently embedded (confirmed empty via `codesign -d --entitlements`). Proposed entitlement
set for the eventual signing milestone — every entry justified individually, none speculative:

| Entitlement | Reason | Affected executable | Required for signing? | Required for notarization? | Security cost |
|---|---|---|---|---|---|
| `com.apple.security.cs.allow-jit` | **Not proposed.** No JIT compilation occurs anywhere in this app's dependency chain (`numba`/`llvmlite` already excluded). | — | — | — | — |
| `com.apple.security.cs.disable-library-validation` | **Not proposed** unless a real post-signing load failure demonstrates a need (see Hardened Runtime above). | — | — | — | — |
| (none required) | Hardened runtime + correct nested-binary signing order is expected to be sufficient on current evidence — no entitlement gap identified. | n/a | n/a | n/a | n/a |

This is a deliberately empty/near-empty proposal: the evidence gathered (no JIT dependencies in the
shipped bundle, no elevated OS resource access anywhere in the WebView-facing capability set, a
private stdin/stdout sidecar channel, no camera/microphone/network-server/sandboxed-file-access
code path) does not support any entitlement beyond hardened runtime itself. If real signing/testing
later surfaces a load failure, add the specific entitlement then, evidence-based — not now,
speculatively.

## Notarization Discovery

Modern (`notarytool`-based, Apple's current and only supported path — the older `altool` submission
flow is deprecated) requirements:

1. **A signed application** — Developer ID Application certificate, hardened runtime, correct
   nested-binary signing order (above).
2. **A packaging format** — `.zip` or `.dmg` (both accepted by `notarytool`; see the release-
   workflow analysis for which this project should use).
3. **`notarytool submit <path> --apple-id <id> --team-id <team> --password <app-specific-password>
   --wait`** (or, preferably, `--keychain-profile <name>` after a one-time `notarytool
   store-credentials` setup) — submits and polls for a result.
4. **Apple ID / App Store Connect API credentials** — either an Apple ID + an app-specific password
   + team ID, or (Apple's more modern, CI-friendlier option) an App Store Connect API key
   (`.p8` key file + Key ID + Issuer ID). Both require an active Apple Developer Program
   membership.
5. **Result check** — `notarytool` returns `Accepted` or `Invalid`; on `Invalid`,
   `notarytool log <submission-id>` retrieves the detailed rejection reasons.
6. **Stapling** — `stapler staple <path>` attaches the notarization ticket to the artifact itself,
   so Gatekeeper can verify it offline (without a network round-trip) on the end-user's machine.
7. **Validation** — `spctl -a -vv --type execute <path>` and `stapler validate <path>` on the final
   artifact.

No submission, real credential use, or Apple contact was performed — this section documents the
workflow shape only, per the mandate's explicit "no real notarization" constraint.

## Credential Strategy (design only, nothing implemented)

Hard rule respected throughout this discovery: no `APPLE_ID`, password, certificate password, or
API private key was searched for, printed, or stored. Recommended future design:

- **Local release builds**: use `notarytool store-credentials <profile-name>` once, interactively,
  outside of any script — this stores the credential in the *local machine's* Keychain, referenced
  thereafter only by profile name (`--keychain-profile <profile-name>`), never as a literal
  argument or environment variable a script could log or leak. The Developer ID signing
  certificate itself lives in the local login Keychain, selected by identity string
  (`codesign --sign "Developer ID Application: <Org> (<TEAMID>)"`), never exported to a file
  checked into the repository.
- **Future GitHub Actions release build**: GitHub Actions **encrypted repository/environment
  secrets** for the App Store Connect API key (`.p8` contents, Key ID, Issuer ID) and the signing
  certificate (`.p12`, base64-encoded, plus its password) — imported into a **temporary, per-run
  Keychain** created and destroyed within the job (the standard `actions/import-codesign-certs` /
  manual `security create-keychain` pattern), never written to the repository or a persistent
  runner disk. `notarytool`'s API-key auth mode (`--key`, `--key-id`, `--issuer`) is preferable to
  Apple-ID+app-specific-password for CI, since it doesn't require an app-specific-password tied to
  a personal Apple ID.
- **Never**: hard-code any of the above into a tracked file, print them in build logs, or pass them
  as plain CLI arguments that would appear in shell history/process listings on a shared machine.

No secret-handling code was written in this discovery pass — this is design-only, per the mandate.

## Download/Quarantine Simulation (proposed test method, not performed)

To evaluate real Gatekeeper behavior without actually distributing a release or modifying this
machine unnecessarily, two safe options exist for a later milestone:

1. **`xattr` quarantine simulation**: `xattr -w com.apple.quarantine "0081;$(date
   +%s);Safari;" <copy-of-the-app>` on a disposable copy of the artifact, then run `spctl -a -vv`
   and attempt to open it, to approximate (not perfectly reproduce) what a downloaded file
   experiences. This is safe (affects only the disposable copy's extended attribute) and
   reversible (`xattr -d com.apple.quarantine`).
2. **A real download round-trip**: once a real release artifact is signed/notarized and actually
   published (e.g. to a private pre-release location), download it through an actual browser on a
   clean or VM'd Mac and observe real Gatekeeper/notarization-ticket behavior — the only fully
   faithful test, appropriate once the pipeline is far enough along to have something worth
   testing this way.

Neither was performed in this discovery pass (no artifact was built or modified beyond what already
existed from the Build 025 final-validation rebuild), consistent with "propose method first."

## Security Review Answer

**Does production distribution require any new WebView capability?** No new WebView-facing
capability was identified by this analysis. Signing, hardened runtime, entitlements, and
notarization are all Rust/build/packaging-layer and OS-level concerns — none of them touch
`desktop/src-tauri/capabilities/main-capability.json`. The existing four-permission set
(`core:default`, `dialog:allow-open`, `dialog:allow-save`, `core:window:allow-destroy`) is expected
to remain unchanged through Build 026's signing/notarization preparation work.

Network surface: notarization submission itself is a one-way, build-time-only network call from the
release operator's machine (or future CI runner) to Apple's notary service — it introduces no
runtime network surface in the shipped application itself. CSP and the app's `connect-src` remain
unaffected.
