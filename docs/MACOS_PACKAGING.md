# macOS Packaging – Build 013

## Mandatory clean environment

Do not package from the development `.venv`.

```bash
make packaging-venv
```

PyInstaller can collect modules that are present in its active environment. The clean packaging environment is therefore part of the engineering standard.

## Diagnostic sequence

### 1. Build console-debug app

```bash
make macos-debug
```

### 2. Run diagnostics

```bash
"dist/ZeroRodCAD Desktop Debug.app/Contents/MacOS/ZeroRodCAD Desktop" --diagnose
```

### 3. Run startup smoke test

```bash
QT_QPA_PLATFORM=offscreen "dist/ZeroRodCAD Desktop Debug.app/Contents/MacOS/ZeroRodCAD Desktop" --startup-test
```

Expected:

```text
STARTUP_OK
```

### 4. Build release app

```bash
make macos-app
```

### 5. Verify release app

```bash
make macos-verify
```

## Size report

The build writes:

```text
build/reports/macos-bundle-size.txt
```

The default budget is 800,000 KB. Override only with an explicit engineering decision:

```bash
ZERORODCAD_APP_SIZE_BUDGET_KB=900000 make macos-app
```

## Why the application is still substantial

CadQuery relies on Open Cascade/OCP, a full solid-modeling kernel. PySide6 also supplies native Qt frameworks. The goal is therefore not an unrealistically tiny bundle, but a controlled bundle without unrelated WebEngine, QML, multimedia, notebook or plotting payloads.
