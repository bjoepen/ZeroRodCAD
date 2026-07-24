"""CadQuery geometry helpers."""

from __future__ import annotations

from collections.abc import Sequence

import cadquery as cq

Point = tuple[float, float, float]


def cylinder_between(start: Point, end: Point, radius: float) -> cq.Workplane:
    sx, sy, sz = start
    ex, ey, ez = end
    direction = cq.Vector(ex - sx, ey - sy, ez - sz)
    length = direction.Length
    if length <= 0:
        raise ValueError("Cylinder start and end must differ.")
    solid = cq.Solid.makeCylinder(
        radius,
        length,
        cq.Vector(sx, sy, sz),
        direction.normalized(),
    )
    return cq.Workplane(obj=solid)


def fuse_all(solids: Sequence[cq.Workplane]) -> cq.Workplane:
    if not solids:
        raise ValueError("At least one solid is required.")
    result = solids[0]
    for solid in solids[1:]:
        result = result.union(solid)
    return result
