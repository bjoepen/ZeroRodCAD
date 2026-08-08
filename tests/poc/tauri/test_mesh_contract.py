"""Tests for zerorod-mesh/v1 conversion and validation (TE-002 sections 12-13)."""

from __future__ import annotations

import math

from tools.poc.tauri.sidecar.mesh_contract import (
    MESH_SCHEMA,
    scene_to_mesh_contract,
    validate_mesh_contract,
)

from zerorodcad.preview_data import PreviewMesh, PreviewScene


def _triangle_scene() -> PreviewScene:
    mesh = PreviewMesh(
        name="tri",
        vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        triangles=((0, 1, 2),),
    )
    lines = {"edges": (((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),)}
    return PreviewScene(meshes=(mesh,), lines=lines)


def test_scene_to_mesh_contract_shape():
    payload = scene_to_mesh_contract(_triangle_scene())
    assert payload["schema"] == MESH_SCHEMA
    assert len(payload["meshes"]) == 1
    mesh = payload["meshes"][0]
    assert mesh["name"] == "tri"
    assert mesh["positions"] == [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    assert mesh["indices"] == [0, 1, 2]
    assert len(payload["lines"]) == 1
    assert payload["lines"][0]["name"] == "edges"
    assert payload["lines"][0]["positions"] == [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]


def test_bounds_cover_mesh_and_line_points():
    payload = scene_to_mesh_contract(_triangle_scene())
    assert payload["bounds"]["min"] == [0.0, 0.0, 0.0]
    assert payload["bounds"]["max"] == [1.0, 1.0, 1.0]


def test_empty_scene_has_zero_bounds():
    payload = scene_to_mesh_contract(PreviewScene(meshes=(), lines={}))
    assert payload["bounds"] == {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}


def test_valid_payload_has_no_problems():
    payload = scene_to_mesh_contract(_triangle_scene())
    assert validate_mesh_contract(payload) == []


def test_wrong_schema_flagged():
    payload = scene_to_mesh_contract(_triangle_scene())
    payload["schema"] = "wrong"
    problems = validate_mesh_contract(payload)
    assert any("schema" in p for p in problems)


def test_empty_meshes_flagged():
    payload = {
        "schema": MESH_SCHEMA,
        "meshes": [],
        "lines": [],
        "bounds": {"min": [0, 0, 0], "max": [0, 0, 0]},
    }
    problems = validate_mesh_contract(payload)
    assert any("non-empty" in p for p in problems)


def test_positions_not_multiple_of_three_flagged():
    payload = {
        "schema": MESH_SCHEMA,
        "meshes": [{"name": "m", "positions": [0.0, 0.0], "indices": [0, 0, 0]}],
        "lines": [],
        "bounds": {"min": [0, 0, 0], "max": [0, 0, 0]},
    }
    problems = validate_mesh_contract(payload)
    assert any("multiple of 3" in p and "positions" in p for p in problems)


def test_indices_not_multiple_of_three_flagged():
    payload = {
        "schema": MESH_SCHEMA,
        "meshes": [{"name": "m", "positions": [0.0, 0.0, 0.0], "indices": [0, 0]}],
        "lines": [],
        "bounds": {"min": [0, 0, 0], "max": [0, 0, 0]},
    }
    problems = validate_mesh_contract(payload)
    assert any("multiple of 3" in p and "indices" in p for p in problems)


def test_out_of_range_index_flagged():
    payload = {
        "schema": MESH_SCHEMA,
        "meshes": [{"name": "m", "positions": [0.0, 0.0, 0.0], "indices": [0, 1, 2]}],
        "lines": [],
        "bounds": {"min": [0, 0, 0], "max": [0, 0, 0]},
    }
    problems = validate_mesh_contract(payload)
    assert any("out of range" in p for p in problems)


def test_nan_position_flagged():
    payload = {
        "schema": MESH_SCHEMA,
        "meshes": [{"name": "m", "positions": [math.nan, 0.0, 0.0], "indices": [0, 0, 0]}],
        "lines": [],
        "bounds": {"min": [0, 0, 0], "max": [0, 0, 0]},
    }
    problems = validate_mesh_contract(payload)
    assert any("NaN" in p for p in problems)


def test_inf_position_flagged():
    payload = {
        "schema": MESH_SCHEMA,
        "meshes": [{"name": "m", "positions": [math.inf, 0.0, 0.0], "indices": [0, 0, 0]}],
        "lines": [],
        "bounds": {"min": [0, 0, 0], "max": [0, 0, 0]},
    }
    problems = validate_mesh_contract(payload)
    assert any("NaN" in p or "Inf" in p for p in problems)


def test_missing_bounds_flagged():
    payload = {
        "schema": MESH_SCHEMA,
        "meshes": [{"name": "m", "positions": [0.0, 0.0, 0.0], "indices": [0, 0, 0]}],
        "lines": [],
    }
    problems = validate_mesh_contract(payload)
    assert any("bounds" in p for p in problems)


def test_real_default_zerorod_scene_is_valid():
    from zerorodcad.parameters import default_parameters
    from zerorodcad.preview import build_preview_scene

    scene = build_preview_scene(default_parameters())
    payload = scene_to_mesh_contract(scene)
    assert validate_mesh_contract(payload) == []
    assert {m["name"] for m in payload["meshes"]} == {"body", "rod"}
    assert {line_entry["name"] for line_entry in payload["lines"]} == {"strings"}
