# -*- mode: python ; coding: utf-8 -*-
# TE-002.1 Variant B — identical to sidecar.spec (same Python, same patched
# cadquery-ocp-novtk env, same hiddenimports/excludes/runtime_hooks) except
# packaged as PyInstaller onedir (COLLECT) instead of onefile, to isolate
# the effect of removing self-extraction from every other variable.

from pathlib import Path

project_root = Path(SPECPATH).parents[2]

analysis = Analysis(
    [str(project_root / "tools" / "poc" / "tauri" / "sidecar" / "__main__.py")],
    pathex=[str(project_root / "src"), str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "OCP",
        "OCP.BRep",
        "OCP.BRepMesh",
        "OCP.STEPControl",
        "OCP.StlAPI",
        "OCP.TKernel",
        "cadquery",
        "cadquery.exporters",
        "cadquery.occ_impl",
        "casadi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        str(project_root / "packaging" / "macos" / "runtime_hook.py"),
    ],
    excludes=[
        "vtk",
        "vtkmodules",
        "PySide6",
        "IPython",
        "jupyter",
        "matplotlib",
        "notebook",
        "pandas",
        "pytest",
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    exclude_binaries=True,
    name="zerorod-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="zerorod-engine",
)
