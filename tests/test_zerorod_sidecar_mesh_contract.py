"""Tests for zerorod_sidecar.mesh_contract's zerorod-mesh/v1 transport (Build 022 M2)."""

from __future__ import annotations

import math

from zerorod_sidecar.mesh_contract import (
    MESH_SCHEMA,
    scene_to_mesh_contract,
    validate_mesh_contract,
)
from zerorodcad.parameters import default_parameters
from zerorodcad.preview import build_preview_scene


def test_scene_to_mesh_contract_uses_the_real_engine_and_is_valid():
    scene = build_preview_scene(default_parameters())
    payload = scene_to_mesh_contract(scene)
    assert payload["schema"] == MESH_SCHEMA
    assert validate_mesh_contract(payload) == []
    assert {m["name"] for m in payload["meshes"]} >= {"body", "rod"}


def test_scene_to_mesh_contract_bounds_cover_meshes_and_lines():
    scene = build_preview_scene(default_parameters())
    payload = scene_to_mesh_contract(scene)
    bounds = payload["bounds"]
    assert len(bounds["min"]) == 3
    assert len(bounds["max"]) == 3
    assert all(bounds["min"][i] <= bounds["max"][i] for i in range(3))


def _valid_payload() -> dict:
    return {
        "schema": MESH_SCHEMA,
        "meshes": [
            {"name": "body", "positions": [0.0, 0.0, 0.0, 1, 0, 0, 0, 1, 0], "indices": [0, 1, 2]}
        ],
        "lines": [{"name": "strings", "positions": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]}],
        "bounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
    }


def test_validate_mesh_contract_accepts_a_well_formed_payload():
    assert validate_mesh_contract(_valid_payload()) == []


def test_validate_mesh_contract_rejects_wrong_schema():
    payload = _valid_payload()
    payload["schema"] = "wrong"
    problems = validate_mesh_contract(payload)
    assert any("schema must be" in p for p in problems)


def test_validate_mesh_contract_rejects_empty_meshes():
    payload = _valid_payload()
    payload["meshes"] = []
    problems = validate_mesh_contract(payload)
    assert any("meshes must be a non-empty list" in p for p in problems)


def test_validate_mesh_contract_rejects_positions_not_multiple_of_three():
    payload = _valid_payload()
    payload["meshes"][0]["positions"] = [0.0, 0.0]
    problems = validate_mesh_contract(payload)
    assert any("not a multiple of 3" in p for p in problems)


def test_validate_mesh_contract_rejects_index_out_of_range():
    payload = _valid_payload()
    payload["meshes"][0]["indices"] = [0, 1, 99]
    problems = validate_mesh_contract(payload)
    assert any("index out of range" in p for p in problems)


def test_validate_mesh_contract_rejects_nan_positions():
    payload = _valid_payload()
    payload["meshes"][0]["positions"] = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, math.nan, 1.0, 0.0]
    problems = validate_mesh_contract(payload)
    assert any("NaN/Inf" in p for p in problems)


def test_validate_mesh_contract_rejects_missing_bounds():
    payload = _valid_payload()
    del payload["bounds"]
    problems = validate_mesh_contract(payload)
    assert any("bounds must have" in p for p in problems)
