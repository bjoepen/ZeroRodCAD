# Build 014 – Preview Recovery

## Incident

Build 013 introduced a regression: the 3D preview no longer built.

## Root cause 1: signal mismatch

The worker declared:

```python
finished = Signal(int, object)
```

while the main window connected:

```python
job.signals.completed.connect(...)
```

The preview job therefore could not be connected correctly.

Build 014 restores one consistent public signal:

```python
completed = Signal(int, object)
```

## Root cause 2: incomplete lazy loading

`PreviewWidget` imported preview data from `zerorodcad.preview`. That module imports CadQuery. The GUI therefore still loaded CadQuery/OCP before displaying the first window.

Preview data types now live in:

```text
zerorodcad/preview_data.py
```

This module has no CadQuery dependency.

## Packaging conclusion

The measured VTK payload is large, but the current CadQuery code imports `vtkmodules` as part of its shape implementation. Blindly excluding VTK can restore a small bundle while breaking preview and CAD operations.

Build 014 therefore prioritizes a working application. A VTK-free runtime will be evaluated as an isolated engineering change in Build 015.

## Definition of Done

- [x] Preview signal contract corrected.
- [x] Preview data decoupled from CadQuery imports.
- [x] Preview errors logged.
- [x] Version tests corrected.
- [x] Error 141 corrected.
- [x] Unsafe dependency pruning reverted.
- [ ] Source preview validated on macOS.
- [ ] Packaged preview validated on macOS.
- [ ] STL and STEP exports validated.
