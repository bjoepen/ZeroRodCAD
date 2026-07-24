# -*- mode: python ; coding: utf-8 -*-

exec(
    compile(
        open("packaging/macos/ZeroRodCAD.spec", encoding="utf-8").read().replace(
            'console=False,',
            'console=True,',
        ).replace(
            'name="ZeroRodCAD Desktop.app",',
            'name="ZeroRodCAD Desktop Debug.app",',
        ),
        "packaging/macos/ZeroRodCAD.spec",
        "exec",
    )
)
