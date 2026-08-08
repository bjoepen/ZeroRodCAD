# -*- mode: python ; coding: utf-8 -*-
# TE-002 PoC only — not part of the production packaging pipeline.
# Builds the zerorod-sidecar/v1 stdin/stdout process as a single-file
# executable for use as a Tauri v2 externalBin. Reuses the same
# TE-001.1-patched cadquery-ocp-novtk environment (.venv-novtk-bundle) and
# the same Build 021 M1 runtime hook TE-001.2 already used — no new
# packaging architecture.

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
    analysis.binaries,
    analysis.datas,
    name="zerorod-engine-aarch64-apple-darwin",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
