"""zerorod-mesh/v1 — adapts zerorodcad.preview_data.PreviewScene into the
transport contract from TE-002 section 12, and validates it per section 13.

Deliberately simple: flat float/int arrays, no base64, no binary encoding.
"""

from __future__ import annotations

import math
from typing import Any

from zerorodcad.preview_data import PreviewScene

MESH_SCHEMA = "zerorod-mesh/v1"


def scene_to_mesh_contract(scene: PreviewScene) -> dict[str, Any]:
    all_points: list[tuple[float, float, float]] = []

    meshes = []
    for mesh in scene.meshes:
        positions: list[float] = []
        for vertex in mesh.vertices:
            positions.extend(float(c) for c in vertex)
            all_points.append(vertex)
        indices: list[int] = []
        for triangle in mesh.triangles:
            indices.extend(int(i) for i in triangle)
        meshes.append({"name": mesh.name, "positions": positions, "indices": indices})

    lines = []
    for name, segments in scene.lines.items():
        positions = []
        for start, end in segments:
            positions.extend(float(c) for c in start)
            positions.extend(float(c) for c in end)
            all_points.append(start)
            all_points.append(end)
        lines.append({"name": name, "positions": positions})

    if not all_points:
        bounds = {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}
    else:
        xs, ys, zs = zip(*all_points, strict=True)
        bounds = {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        }

    return {
        "schema": MESH_SCHEMA,
        "meshes": meshes,
        "lines": lines,
        "bounds": bounds,
    }


def validate_mesh_contract(payload: dict[str, Any]) -> list[str]:
    """Returns a list of validation problems (empty = valid), per section 13.
    Never raises — the caller decides whether problems are fatal."""
    problems: list[str] = []

    if payload.get("schema") != MESH_SCHEMA:
        problems.append(f"schema must be '{MESH_SCHEMA}', got {payload.get('schema')!r}")

    meshes = payload.get("meshes")
    if not isinstance(meshes, list) or len(meshes) == 0:
        problems.append("meshes must be a non-empty list")
        meshes = []

    for mesh in meshes:
        name = mesh.get("name", "<unnamed>")
        positions = mesh.get("positions")
        indices = mesh.get("indices")

        if not isinstance(positions, list) or len(positions) == 0:
            problems.append(f"mesh '{name}': positions must be non-empty")
            positions = []
        elif len(positions) % 3 != 0:
            problems.append(f"mesh '{name}': positions length {len(positions)} not a multiple of 3")
        if any(not isinstance(v, int | float) or math.isnan(v) or math.isinf(v) for v in positions):
            problems.append(f"mesh '{name}': positions contain NaN/Inf/non-numeric values")

        if not isinstance(indices, list) or len(indices) == 0:
            problems.append(f"mesh '{name}': indices must be non-empty")
            indices = []
        elif len(indices) % 3 != 0:
            problems.append(f"mesh '{name}': indices length {len(indices)} not a multiple of 3")

        vertex_count = len(positions) // 3
        if any(not isinstance(i, int) or i < 0 or i >= vertex_count for i in indices):
            problems.append(f"mesh '{name}': index out of range [0, {vertex_count})")

    bounds = payload.get("bounds")
    if not isinstance(bounds, dict) or "min" not in bounds or "max" not in bounds:
        problems.append("bounds must have 'min' and 'max'")
    else:
        for key in ("min", "max"):
            value = bounds.get(key)
            if (
                not isinstance(value, list)
                or len(value) != 3
                or any(
                    not isinstance(v, int | float) or math.isnan(v) or math.isinf(v) for v in value
                )
            ):
                problems.append(f"bounds.{key} must be [x, y, z] finite numbers")

    return problems
