# macOS Packaging Guide

## Prerequisites

- macOS
- working ZeroRodCAD virtual environment
- CadQuery and PySide6 installed
- PyInstaller installed through the `packaging` extra

```bash
source .venv/bin/activate
python -m pip install -e ".[dev,desktop,packaging]"
```

## Build

```bash
./scripts/build_macos_app.sh
```

The script:

1. verifies macOS,
2. activates `.venv`,
3. creates the `.icns` icon,
4. clears old build products,
5. runs PyInstaller,
6. writes the application to `dist/`.

## Verify

```bash
./scripts/verify_macos_app.sh
```

Verify manually:

- launch the app,
- open the example project,
- rotate and zoom the preview,
- change body depth,
- export STL and STEP,
- close and reopen the app,
- drag a `.zerorod` file onto the app,
- inspect exported files independently.

## Release ZIP

```bash
./scripts/package_macos_release.sh
```

The `ditto` command preserves macOS metadata.

## Signing

Unsigned local builds can be tested on the build Mac. Distribution to other users should use an Apple Developer ID.

Example structure:

```bash
codesign   --deep   --force   --options runtime   --sign "Developer ID Application: YOUR NAME (TEAMID)"   "dist/ZeroRodCAD Desktop.app"
```

The exact signing identity and entitlements depend on the owner's Apple Developer account.

## Notarization

After signing, create a ZIP and submit it with `notarytool`.

Do not store Apple credentials in the repository. Use a Keychain profile or GitHub repository secrets.

## Universal build

A universal release should be produced and tested for both:

- Apple Silicon (`arm64`)
- Intel (`x86_64`)

CadQuery/OCP binary availability must be verified independently for both architectures.
