# -*- mode: python ; coding: utf-8 -*-
# Build 022 M2 — productive sidecar packaging.
#
# TE-002.2B's packaging baseline (docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md
# "Packaging strategy"), reused for the productive sidecar rather than
# reinvented: onedir only (no onefile fallback), same excludes
# (vtk/vtkmodules/PySide6/numba/llvmlite/scipy + the usual dev/notebook
# noise), same runtime hook (opt-in runtime-trace evidence, no-op unless
# explicitly enabled via env var). Entry point is the productive
# src/zerorod_sidecar package, not tools/poc/tauri/sidecar (which stays the
# read-only research reference — see
# tools/poc/tauri/sidecar-onedir.spec for the PoC's own, untouched spec).

from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

project_root = Path(SPECPATH).parents[1]

# Needed so the frozen sidecar's own `status` command can report an accurate
# ocp_variant via importlib.metadata — without this, PyInstaller does not
# collect cadquery-ocp-novtk's dist-info and the field silently reads back
# as null inside the bundle (found empirically while validating this spec).
sidecar_datas = copy_metadata("cadquery-ocp-novtk")

analysis = Analysis(
    [str(project_root / "src" / "zerorod_sidecar" / "__main__.py")],
    pathex=[str(project_root / "src"), str(project_root)],
    binaries=[],
    datas=sidecar_datas,
    hiddenimports=[
        "OCP",
        "OCP.BRep",
        "OCP.BRepMesh",
        "OCP.STEPControl",
        "OCP.StlAPI",
        # Build 026 M1: "OCP.TKernel" and "cadquery.exporters" removed —
        # investigated and confirmed OBSOLETE_HIDDEN_IMPORT
        # (docs/migration/BUILD-026-DEPENDENCY-AUDIT.md): "OCP.TKernel" was
        # never a real importable module (pybind11 never registers it; a
        # copy-paste artifact from the legacy PySide6 spec), and
        # "cadquery.exporters" was always the wrong module path (the real
        # module is cadquery.occ_impl.exporters, already collected via
        # "cadquery.occ_impl" below plus PyInstaller's own module-graph
        # analysis of cadquery/__init__.py's `from .occ_impl import
        # exporters`). Removal proven safe by a real rebuild + preview/
        # report/export regression, not by inspection alone.
        "cadquery",
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
        # TE-002.2B Optimization C+D (docs/research/TE-002.2B-Tauri-Bundle-Optimization/
        # Optimization-C-Numba-Llvmlite.md / Optimization-D-Scipy.md): only
        # reachable via cadquery.vis -> cadquery.occ_impl.nurbs, which
        # ZeroRodCAD never imports. Re-open this list with evidence if a
        # future Build 022+ feature actually needs one of these — do not
        # silently drop the exclude.
        "numba",
        "llvmlite",
        "scipy",
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
