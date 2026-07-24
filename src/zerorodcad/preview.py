"""Convert engineering geometry into renderer-independent preview data."""

from __future__ import annotations

from dataclasses import dataclass, field

import cadquery as cq

from .model import build_body, build_rod
from .parameters import ZeroRodParameters

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


def _vector_tuple(vector: cq.Vector) -> Point3D:
    return (float(vector.x), float(vector.y), float(vector.z))


def tessellate_workplane(
    name: str,
    workplane: cq.Workplane,
    tolerance: float = 0.16,
    angular_tolerance: float = 0.35,
) -> PreviewMesh:
    solids = workplane.solids().vals()
    if not solids:
        raise ValueError(f"Preview object '{name}' contains no solid.")

    all_vertices: list[Point3D] = []
    all_triangles: list[Triangle] = []

    for solid in solids:
        vertices, triangles = solid.tessellate(tolerance, angular_tolerance)
        offset = len(all_vertices)
        all_vertices.extend(_vector_tuple(vertex) for vertex in vertices)
        all_triangles.extend(
            (int(a) + offset, int(b) + offset, int(c) + offset) for a, b, c in triangles
        )

    return PreviewMesh(
        name=name,
        vertices=tuple(all_vertices),
        triangles=tuple(all_triangles),
    )


def build_virtual_strings(p: ZeroRodParameters) -> tuple[Line3D, ...]:
    lines: list[Line3D] = []
    start_y = p.string_inlet_y - 4.0
    end_y = p.body_depth + 5.0

    for x, support_z in zip(
        p.string_positions_x,
        p.string_support_heights,
        strict=True,
    ):
        lines.append(
            (
                (x, start_y, p.string_inlet_z),
                (x, p.channel_contact_y, p.channel_contact_z),
            )
        )
        lines.append(
            (
                (x, p.channel_contact_y, p.channel_contact_z),
                (x, end_y, support_z),
            )
        )

    return tuple(lines)


def build_preview_scene(p: ZeroRodParameters) -> PreviewScene:
    body = tessellate_workplane("body", build_body(p))
    rod = tessellate_workplane("rod", build_rod(p), tolerance=0.10)
    return PreviewScene(
        meshes=(body, rod),
        lines={"strings": build_virtual_strings(p)},
    )
