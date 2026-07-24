# Build 015 – Lean Runtime Audit

## Objective

Reduce the macOS application size based on evidence rather than trial-and-error exclusions.

## Known bundle findings

The Build 014 report showed large contributions from:

- VTK,
- OCP,
- llvmlite,
- CasADi,
- Qt.

OCP and parts of VTK belong to the currently working CAD runtime. CasADi, llvmlite and Numba are not used by ZeroRodCAD directly and are therefore excluded in this build.

## Audit outputs

### Dependency tree

```text
build/reports/dependencies/pipdeptree.txt
build/reports/dependencies/pipdeptree.json
```

### Installed distribution sizes

```text
build/reports/dependencies/distribution-sizes.txt
```

### Runtime imports

```text
build/reports/dependencies/runtime-import-probe.txt
```

### PyInstaller analysis

```text
build/reports/pyinstaller/
```

### Bundle files and frameworks

```text
build/reports/macos-bundle-size.txt
build/reports/macos-bundle-all-files.txt
build/reports/pyinstaller/framework-summary.txt
```

## Validation order

1. Build the clean packaging environment.
2. Run the dependency audit.
3. Build the debug application.
4. Confirm debug startup.
5. Build the release application.
6. Run automated verification.
7. Confirm the interactive preview manually.
8. Export STL and STEP.
9. Compare bundle size with Build 014.

## Definition of Done

- [x] Audit scripts included.
- [x] CasADi excluded.
- [x] llvmlite excluded.
- [x] Numba excluded.
- [x] VTK retained.
- [x] Preview-engine validation included.
- [ ] Dependency reports generated on macOS.
- [ ] Release app built.
- [ ] 3D preview verified.
- [ ] STL and STEP verified.
- [ ] Final bundle size recorded.
