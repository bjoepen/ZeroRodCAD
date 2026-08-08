"""Tests for tools/poc/tauri/sidecar/main.py's request dispatch (TE-002 section 29)."""

from __future__ import annotations

import json

from tools.poc.tauri.sidecar.main import handle_request
from tools.poc.tauri.sidecar.protocol import SIDECAR_SCHEMA


def _request(**overrides) -> str:
    base = {"schema": SIDECAR_SCHEMA, "request_id": "rid-1", "command": "preview", "parameters": {}}
    base.update(overrides)
    return json.dumps(base)


def test_unknown_command_returns_error_not_exception():
    response = handle_request(_request(command="does-not-exist"))
    assert response["ok"] is False
    assert response["error"]["code"] == "unknown_command"
    assert response["request_id"] == "rid-1"


def test_invalid_json_line_returns_error():
    response = handle_request("this is not { valid json")
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_json"
    assert response["request_id"] is None


def test_invalid_parameters_type_returns_error():
    response = handle_request(_request(parameters="not-a-dict"))
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_request"


def test_preview_with_unsupported_parameters_returns_clean_error():
    response = handle_request(_request(parameters={"body_width": 999}))
    assert response["ok"] is False
    assert response["error"]["code"] == "unsupported_parameters"


def test_real_preview_command_returns_valid_mesh():
    response = handle_request(_request())
    assert response["ok"] is True
    assert response["schema"] == SIDECAR_SCHEMA
    assert response["request_id"] == "rid-1"
    result = response["result"]
    assert result["schema"] == "zerorod-mesh/v1"
    assert len(result["meshes"]) > 0
    assert "timing" in result


def test_preview_response_never_contains_traceback_text():
    response = handle_request(_request(command="does-not-exist"))
    serialized = json.dumps(response)
    assert "Traceback" not in serialized
    assert 'File "' not in serialized


def test_response_is_deterministic_in_shape_across_calls():
    first = handle_request(_request())
    second = handle_request(_request())
    assert {m["name"] for m in first["result"]["meshes"]} == {
        m["name"] for m in second["result"]["meshes"]
    }
    assert first["result"]["bounds"] == second["result"]["bounds"]
