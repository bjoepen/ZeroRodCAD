"""Headless preview-engine validation for source and packaged runtimes."""

from __future__ import annotations

from zerorodcad.parameters import ZeroRodParameters
from zerorodcad.preview import build_preview_scene


def main() -> int:
    parameters = ZeroRodParameters()
    scene = build_preview_scene(parameters)

    if not scene.meshes:
        raise RuntimeError("Preview scene contains no meshes.")

    vertices = sum(len(mesh.vertices) for mesh in scene.meshes)
    triangles = sum(len(mesh.triangles) for mesh in scene.meshes)
    string_segments = len(scene.lines.get("strings", ()))

    if vertices == 0 or triangles == 0:
        raise RuntimeError("Preview tessellation returned empty geometry.")

    print("PREVIEW_ENGINE_OK")
    print(f"Meshes: {len(scene.meshes)}")
    print(f"Vertices: {vertices}")
    print(f"Triangles: {triangles}")
    print(f"String segments: {string_segments}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
