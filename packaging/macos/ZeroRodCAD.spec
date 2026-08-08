# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

project_root = Path(SPECPATH).parents[1]
icon_path = project_root / "assets" / "macos" / "ZeroRodCAD.icns"

# TE-001.2: opt-in, env-gated no-VTK packaging variant. Default behavior
# (env var unset) is unchanged — the productive spec still hidden-imports
# vtkmodules. Set ZERORODCAD_NOVTK_BUNDLE=1 to build against
# cadquery-ocp-novtk + the TE-001.1 patch instead, where vtkmodules is
# intentionally absent and must not be hidden-imported.
_novtk_bundle = bool(os.environ.get("ZERORODCAD_NOVTK_BUNDLE"))

excluded_modules = [
    "IPython",
    "jupyter",
    "matplotlib",
    "notebook",
    "pandas",
    "pytest",
    "tkinter",
    "llvmlite",
    "numba",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtXml",
]

if _novtk_bundle:
    # TE-001.2: defense-in-depth only — vtk/vtkmodules aren't installed in
    # this environment at all, so this is inert, but makes the no-VTK intent
    # explicit and guards against any hook pulling them in unexpectedly.
    excluded_modules += ["vtk", "vtkmodules"]

info_plist = {
    "CFBundleName": "ZeroRodCAD Desktop",
    "CFBundleDisplayName": "ZeroRodCAD Desktop",
    "CFBundleIdentifier": "de.beblog.zerorodcad",
    "CFBundleShortVersionString": "0.15.0",
    "CFBundleVersion": "015",
    "NSHighResolutionCapable": True,
    "CFBundleDocumentTypes": [
        {
            "CFBundleTypeName": "ZeroRodCAD Project",
            "CFBundleTypeRole": "Editor",
            "LSHandlerRank": "Owner",
            "LSItemContentTypes": ["de.beblog.zerorodcad.project"],
            "CFBundleTypeExtensions": ["zerorod"],
        }
    ],
}

analysis = Analysis(
    [str(project_root / "src" / "zerorodcad_desktop" / "launcher.py")],
    pathex=[str(project_root / "src")],
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
    ]
    + ([] if _novtk_bundle else ["vtkmodules.vtkCommonCore", "vtkmodules.vtkCommonDataModel"]),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        str(project_root / "packaging" / "macos" / "runtime_hook.py"),
    ],
    excludes=excluded_modules,
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ZeroRodCAD Desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="ZeroRodCAD Desktop",
)

app = BUNDLE(
    collection,
    name="ZeroRodCAD Desktop.app",
    icon=str(icon_path),
    bundle_identifier="de.beblog.zerorodcad",
    info_plist=info_plist,
)
