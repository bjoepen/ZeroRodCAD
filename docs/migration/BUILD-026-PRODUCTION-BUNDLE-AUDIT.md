# Build 026 — Production Bundle Audit

Discovery document. No production source, packaging, or configuration was changed to produce this
audit. All findings are against the freshly rebuilt, current-HEAD Build 025 final release bundle
(`scripts/build-productive-desktop-app.sh release` output,
`desktop/src-tauri/target/release/bundle/macos/ZeroRodCAD.app`), inspected read-only with `plutil`,
`codesign`, `spctl`, `otool`, `lipo`, `file`, `find`, `xattr`.

## Info.plist (full)

```text
CFBundleDevelopmentRegion => "English"
CFBundleDisplayName       => "ZeroRodCAD"
CFBundleExecutable        => "zerorod-desktop"
CFBundleIconFile          => "icon.icns"
CFBundleIdentifier        => "dev.zerorodcad.desktop"
CFBundleInfoDictionaryVersion => "6.0"
CFBundleName              => "ZeroRodCAD"
CFBundlePackageType       => "APPL"
CFBundleShortVersionString => "0.1.0"
CFBundleVersion           => "0.1.0"
CSResourcesFileMapped     => true
LSMinimumSystemVersion    => "10.13"
LSRequiresCarbon          => true
NSHighResolutionCapable   => true
```

Two items stand out as likely Tauri/`cargo-bundle` template defaults, not deliberate product
decisions: `LSMinimumSystemVersion = 10.13` (2017, far below any realistic Apple Silicon floor) and
`LSRequiresCarbon = true` (Carbon is a defunct pre-OS X API family; an arm64 Rust/WebKit app cannot
run on a Carbon-era system regardless of this key). Both are classified `DECISION_REQUIRED` in the
gap report — corrected values, not their removal, need an explicit decision.

## Bundle Identifier

- Current: `dev.zerorodcad.desktop`
- Source: `desktop/src-tauri/tauri.conf.json`'s `"identifier"` field — correctly propagated into
  `Info.plist`'s `CFBundleIdentifier`. No inconsistency between config and compiled artifact.
- Assessment: the `dev.` prefix (rather than an org reverse-DNS such as `com.zerorodcad.app` or
  `dev.zerorodcad.app` without the ambiguous "development" reading) reads as a placeholder chosen at
  Build 022 bring-up, not a considered final public identifier. `DECISION_REQUIRED` — changing the
  bundle identifier after any real-world install would break that install's association with
  future updates (macOS treats bundle identifier as the app's durable identity for Gatekeeper,
  LaunchServices, and any future sandbox/keychain-group entitlements), so this should be decided
  once, deliberately, before Build 026 produces anything distributed — not iterated on later.

## Version Fields

| Source | Value |
|---|---|
| `Info.plist` `CFBundleShortVersionString` / `CFBundleVersion` | `0.1.0` / `0.1.0` |
| `desktop/src-tauri/Cargo.toml` `package.version` | `0.1.0` |
| `desktop/src-tauri/tauri.conf.json` `"version"` | `0.1.0` |
| `desktop/frontend/package.json` `"version"` | `0.1.0` |
| `app_info()` (`commands.rs`) | `build = "025"`, `milestone = "M5"` |

All four `0.1.0` sources are mutually consistent (no drift). `0.1.0` has never been bumped since
Build 022 and carries no relationship to Build 022–025 progress — it is a distinct axis from the
`app_info()` engineering-identity pair. See "Versioning Strategy" in the release-workflow analysis
for the proposed reconciliation; not decided here.

## Application / Executable Name

`CFBundleName`/`CFBundleDisplayName` = `ZeroRodCAD`, `CFBundleExecutable` = `zerorod-desktop`,
actual file at `Contents/MacOS/zerorod-desktop`, permissions `-rwxr-xr-x`. Consistent, no findings.

## Minimum macOS Version

`LSMinimumSystemVersion = "10.13"` — see Info.plist note above. `ALREADY_COMPLETE` in the sense the
key exists; `DECISION_REQUIRED` on its correct value.

## Architecture

- Main executable (`Contents/MacOS/zerorod-desktop`): Mach-O 64-bit, **arm64 only**.
- Sidecar (`Contents/Resources/zerorod-engine-onedir/zerorod-engine`): Mach-O 64-bit, **arm64
  only**.
- Not universal2. See "Architecture Target" section below.

## Icon Resources

`Contents/Resources/icon.icns` present, 111,108 bytes, valid `Mac OS X icon` family, correctly
referenced by `CFBundleIconFile`. `ALREADY_COMPLETE`.

## Entitlements

`codesign -d --entitlements :- Contents/MacOS/zerorod-desktop` → exit 1, no entitlements embedded.
Expected for an unsigned/ad-hoc build; full analysis in
`BUILD-026-SIGNING-NOTARIZATION-ANALYSIS.md`.

## Hardened Runtime / Code-Sign Status

```text
codesign -dv --verbose=4:
  Identifier=zerorod_desktop-3b007e3d0fde3062
  Format=app bundle with Mach-O thin (arm64)
  CodeDirectory flags=0x20002(adhoc,linker-signed)
  Signature=adhoc
  TeamIdentifier=not set
  Sealed Resources=none
  Internal requirements=none

spctl -a -vv:
  ZeroRodCAD.app: code has no resources but signature indicates they must be present
  (exit 1)
```

**Not really signed**: the `adhoc,linker-signed` flag is Cargo/Rust's automatic ad-hoc signature —
required for any arm64 Mach-O to execute at all on Apple Silicon, not a Developer ID signature.
`TeamIdentifier=not set`, `Sealed Resources=none`. **Hardened runtime: off** (ad-hoc signatures
cannot carry hardened-runtime flags). `spctl` cannot even fully assess the bundle because an
ad-hoc app-bundle signature lacks a proper resource envelope — this is a stricter failure mode than
the familiar "right-click → Open" unsigned-but-legitimate case.

## Quarantine / Gatekeeper Behavior

`xattr -l` on the bundle and on the main executable: **empty both times — no
`com.apple.quarantine` attribute.** This app was built and launched locally via `open`, never
downloaded through a browser/AirDrop/Mail — macOS never quarantined it. **This is not representative
of a real distributed release.** A `.dmg`/`.zip` a user actually downloads gets quarantined by the
originating app, and Gatekeeper then evaluates the ad-hoc, `TeamIdentifier=not set` binary for
real at first launch — which, given the above, would currently be **rejected outright**, not merely
show a right-click-to-open override (that softer path exists for a legitimately signed-but-not-yet-
notarized app; an ad-hoc binary with no team identity is a stricter case). See
`BUILD-026-SIGNING-NOTARIZATION-ANALYSIS.md` §"Download/Quarantine Simulation" for a safe future
test method.

## Bundle Structure

```text
ZeroRodCAD.app/
  Contents/
    Info.plist
    MacOS/
      zerorod-desktop
    Resources/
      icon.icns
      zerorod-engine-onedir/        <- embedded Python sidecar (PyInstaller onedir)
```

Embedded libraries by category (161 Mach-O total, not enumerated individually): OpenCASCADE
`libTK*.dylib` — 100; `libcasadi*` — 2; `Python.framework`-related — 7; `numpy`-related — 4; total
`.dylib` — 156; total `.so` — 77 (see `BUILD-026-DEPENDENCY-AUDIT.md` for the full component
inventory).

## RPATH / Load Commands

- Main executable: **no `LC_RPATH` entries**. `otool -L` shows only standard, fixed-location macOS
  system frameworks (AppKit, WebKit, CoreFoundation, etc.) — portable by construction.
- Sidecar executable: minimal direct links — only `libSystem.B.dylib` and `libz.1.dylib`.
- Representative OpenCASCADE dylib (`libTKernel.7.9.3.dylib`): links via
  `@rpath/libTKernel.7.9.3.dylib` / `@rpath/libc++.1.0.dylib`, own `LC_RPATH = @loader_path/../..`
  — relative, loader-path-based, portable within the bundle. This is exactly what the dylib-dedup
  step's symlink-safety verification depends on (see `BUILD-026-DEPENDENCY-AUDIT.md`).

## Symlinks

Count: **77**, matches the documented Build 025 figure exactly. Spot-checked 5: all point to
relative targets of the form `OCP/.dylibs/libX.dylib` — portable within the bundle, not absolute
host paths. `ALREADY_COMPLETE`.

## Executable Permissions

Both `zerorod-desktop` and `zerorod-engine`: `-rwxr-xr-x`. No findings.

## Unexpected Writable Files / Debug Artifacts

World/group-writable files: **0**. Debug/dev artifacts (`*.pdb`, `*.map`, `__pycache__`, `*.pyc`):
**0 found**. `ALREADY_COMPLETE`.

## Architecture Target

- Host/build machine: `arm64` (Apple Silicon). No `.cargo/config.toml` target override — `cargo
  build --release` targets native (arm64) only.
- `cadquery-ocp-novtk 7.9.3.1.1`: the installed wheel's own metadata reports
  `Tag: cp313-cp313-macosx_11_0_arm64` (built via `delocate`) — **arm64-only** as currently
  installed. A separate x86_64 wheel of the identical version does exist on PyPI
  (`cadquery_ocp_novtk-7.9.3.1.1-cp313-cp313-macosx_11_0_x86_64.whl`, confirmed reachable) — so
  cross-arch is dependency-feasible, but **no single universal2/fat wheel exists**. A universal
  build would require assembling two separate architecture-specific sidecar builds (PyInstaller
  onedir is not itself fat-binary-capable across a Python C-extension tree) and either fat-linking
  the results or shipping two artifacts — not a drop-in Tauri/Cargo flag.
- Classification: **DEFERRED**. Nothing in the current product, dependency chain, or evidence
  gathered here demonstrates a concrete Intel-Mac distribution requirement. Apple Silicon has been
  the sole shipping architecture for new Macs since 2020; recommend arm64-only for the initial
  Build 026 distributable, revisited only if a real x86_64 user need is demonstrated. Full
  reasoning in `BUILD-026-RELEASE-WORKFLOW-ANALYSIS.md`.

## Summary Classification

| Area | Status |
|---|---|
| Bundle structure / symlinks / RPATHs / permissions | ALREADY_COMPLETE |
| Icon | ALREADY_COMPLETE |
| Version-field internal consistency | ALREADY_COMPLETE |
| Minimum macOS version value / `LSRequiresCarbon` | DECISION_REQUIRED |
| Bundle identifier | DECISION_REQUIRED |
| Code signing | REQUIRED_FOR_DISTRIBUTION (see signing analysis) |
| Hardened runtime | REQUIRED_FOR_DISTRIBUTION (see signing analysis) |
| Architecture (universal2) | DEFERRED |
