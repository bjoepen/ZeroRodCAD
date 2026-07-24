# ZeroRodCAD Desktop

> **Engineering the Perfect String Path**

## Current build

**Build 017 — Repository Cleanup & Optimization**

The application and 3D preview remain functionally stable. Build 017 begins by removing generated resources, simplifying the repository and preparing a smaller, evidence-based macOS bundle.

## Build 017 – Sprint 1

- generated macOS and Python metadata removed,
- comprehensive `.gitignore` added,
- `.gitattributes` added for consistent line endings,
- documentation reorganized by purpose,
- generated exports removed from version control,
- source, tests, packaging specifications and examples preserved.

See [the documentation index](docs/README.md) and the
[Sprint 1 release note](docs/releases/BUILD-017-SPRINT-1.md).

## Clean workflow

```bash
rm -rf build dist release .venv-packaging
make packaging-venv
make dependency-audit
make macos-debug
make macos-app
make macos-verify
```

## Generated reports

```text
build/reports/dependencies/
build/reports/pyinstaller/
build/reports/macos-bundle-size.txt
build/reports/macos-bundle-all-files.txt
build/reports/suspect-dependencies.txt
```

## Development quality gate

```bash
source .venv/bin/activate
make quality
```

## Engineering rule

A dependency may only be removed from the bundle after all of the following pass:

- application startup,
- 3D preview generation,
- parameter-driven preview rebuild,
- STL export,
- STEP export,
- independent inspection of both exports.

## Compatibility

- project format remains version 1,
- no geometry parameters changed,
- projects from Builds 010–014 remain compatible.
