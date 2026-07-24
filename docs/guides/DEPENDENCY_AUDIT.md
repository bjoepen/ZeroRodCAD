# Dependency Audit

## Purpose

This audit answers four questions:

1. Which packages are installed in the packaging environment?
2. Why are they installed?
3. Which packages dominate disk usage?
4. Which packages are actually collected into the application bundle?

## Commands

```bash
make packaging-venv
make dependency-audit
make macos-app
```

## Interpretation

### CasADi

ZeroRodCAD does not import CasADi. Its presence in the bundle is treated as accidental unless the dependency tree proves otherwise.

### llvmlite and Numba

ZeroRodCAD does not import either package. They are explicitly excluded in Build 015.

### OCP

OCP is the Open Cascade binding used by CadQuery and is expected to remain one of the largest components.

### VTK

The current CadQuery environment imports selected `vtkmodules`. VTK remains included until a replacement runtime has passed the complete preview and export validation.

## Evidence before removal

Never remove a large module based only on filename or size. Record:

- dependency path,
- import path,
- PyInstaller cross reference,
- source startup,
- packaged startup,
- preview output,
- STL export,
- STEP export.
