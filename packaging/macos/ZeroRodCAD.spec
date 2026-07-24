# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).parents[1]
icon_path = project_root / "assets" / "macos" / "ZeroRodCAD.icns"
info_plist = {
    "CFBundleName": "ZeroRodCAD Desktop",
    "CFBundleDisplayName": "ZeroRodCAD Desktop",
    "CFBundleIdentifier": "de.beblog.zerorodcad",
    "CFBundleShortVersionString": "0.12.0",
    "CFBundleVersion": "012",
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
    "UTExportedTypeDeclarations": [
        {
            "UTTypeIdentifier": "de.beblog.zerorodcad.project",
            "UTTypeDescription": "ZeroRodCAD Project",
            "UTTypeConformsTo": ["public.json", "public.data"],
            "UTTypeTagSpecification": {
                "public.filename-extension": ["zerorod"],
                "public.mime-type": ["application/x-zerorodcad-project"],
            },
        }
    ],
}

analysis = Analysis(
    [str(project_root / "src" / "zerorodcad_desktop" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (str(project_root / "docs"), "docs"),
        (str(project_root / "examples"), "examples"),
    ],
    hiddenimports=[
        "cadquery",
        "cadquery.occ_impl",
        "OCP",
        "OCP.TKernel",
        "OCP.BRep",
        "OCP.BRepMesh",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
