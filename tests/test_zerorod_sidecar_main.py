"""Tests for zerorod_sidecar.main's request dispatch (Build 022 M2)."""

from __future__ import annotations

import json

from zerorod_sidecar.main import handle_request
from zerorod_sidecar.protocol import SIDECAR_SCHEMA


def _request(**overrides) -> str:
    base = {"schema": SIDECAR_SCHEMA, "request_id": "rid-1", "command": "ping", "parameters": {}}
    base.update(overrides)
    return json.dumps(base)


def test_ping_returns_ok_and_pid():
    response = handle_request(_request(command="ping"))
    assert response["ok"] is True
    assert response["result"]["status"] == "ok"
    assert isinstance(response["result"]["pid"], int)


def test_status_returns_engine_and_build_milestone_info():
    # Reports the *actual* interpreter's state, not a fixed expectation —
    # this repo's default .venv legitimately has VTK/cadquery-ocp installed
    # for the legacy PySide6 app (README "Aktueller Stand"); the No-VTK
    # invariant is proven separately, against the TE-001.1-patched
    # interpreter, by TestRealPersistentSubprocess::test_real_subprocess_no_vtk_or_pyside6.
    response = handle_request(_request(command="status"))
    assert response["ok"] is True
    result = response["result"]
    assert result["status"] == "ready"
    assert result["milestone"] == "build022-m2"
    assert isinstance(result["vtk_installed"], bool)
    assert result["python_version"].startswith("3.13")


def test_status_reports_a_known_ocp_variant():
    response = handle_request(_request(command="status"))
    assert response["result"]["ocp_variant"] in {"cadquery-ocp-novtk", "cadquery-ocp", None}


def test_shutdown_returns_shutting_down_status():
    response = handle_request(_request(command="shutdown"))
    assert response["ok"] is True
    assert response["result"]["status"] == "shutting_down"


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
    response = handle_request(_request(command="ping", parameters="not-a-dict"))
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_request"


def test_preview_with_unsupported_parameters_returns_clean_error():
    response = handle_request(_request(command="preview", parameters={"body_width": 999}))
    assert response["ok"] is False
    assert response["error"]["code"] == "unsupported_parameters"


def test_real_preview_command_returns_valid_mesh():
    response = handle_request(_request(command="preview"))
    assert response["ok"] is True
    assert response["schema"] == SIDECAR_SCHEMA
    assert response["request_id"] == "rid-1"
    result = response["result"]
    assert result["schema"] == "zerorod-mesh/v1"
    assert len(result["meshes"]) > 0
    assert "timing" in result


def test_response_never_contains_traceback_text():
    response = handle_request(_request(command="does-not-exist"))
    serialized = json.dumps(response)
    assert "Traceback" not in serialized
    assert 'File "' not in serialized


def test_response_is_deterministic_in_shape_across_calls():
    first = handle_request(_request(command="preview"))
    second = handle_request(_request(command="preview"))
    assert {m["name"] for m in first["result"]["meshes"]} == {
        m["name"] for m in second["result"]["meshes"]
    }
    assert first["result"]["bounds"] == second["result"]["bounds"]
