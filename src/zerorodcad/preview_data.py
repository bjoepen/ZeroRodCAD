"""Renderer-independent preview data structures."""

from __future__ import annotations

from dataclasses import dataclass, field

Point3D = tuple[float, float, float]
Triangle = tuple[int, int, int]
Line3D = tuple[Point3D, Point3D]


@dataclass(frozen=True)
class PreviewMesh:
    name: str
    vertices: tuple[Point3D, ...]
    triangles: tuple[Triangle, ...]


@dataclass(frozen=True)
class PreviewScene:
    meshes: tuple[PreviewMesh, ...]
    lines: dict[str, tuple[Line3D, ...]] = field(default_factory=dict)
