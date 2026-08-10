"""Tests for zerorod_sidecar.main's request dispatch (Build 022 M2, extended
for zerorod-parameters/v1 in Build 023 M1)."""

from __future__ import annotations

import json

from zerorod_sidecar.main import handle_request
from zerorod_sidecar.parameters_contract import PARAMETERS_SCHEMA
from zerorod_sidecar.protocol import SIDECAR_SCHEMA


def _request(**overrides) -> str:
    base = {"schema": SIDECAR_SCHEMA, "request_id": "rid-1", "command": "ping", "parameters": {}}
    base.update(overrides)
    return json.dumps(base)


def _params(values: dict) -> dict:
    return {"schema": PARAMETERS_SCHEMA, "values": values}


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
    assert result["milestone"] == "build023-m1"
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


# --- Build 023 M1: zerorod-parameters/v1 -----------------------------------


def test_parameters_defaults_command_returns_canonical_values():
    response = handle_request(_request(command="parameters_defaults"))
    assert response["ok"] is True
    result = response["result"]
    assert result["schema"] == PARAMETERS_SCHEMA
    assert result["values"]["body_width"] == 38.0
    assert result["values"]["string_gauges_inch"] == [0.036, 0.026, 0.017]


def test_explicit_canonical_default_preview_matches_parameterless_preview():
    defaults = handle_request(_request(command="parameters_defaults"))["result"]["values"]
    parameterless = handle_request(_request(command="preview"))
    explicit = handle_request(_request(command="preview", parameters=_params(defaults)))

    assert explicit["ok"] is True
    assert explicit["result"]["bounds"] == parameterless["result"]["bounds"]
    assert [m["positions"] for m in explicit["result"]["meshes"]] == [
        m["positions"] for m in parameterless["result"]["meshes"]
    ]
    assert [m["indices"] for m in explicit["result"]["meshes"]] == [
        m["indices"] for m in parameterless["result"]["meshes"]
    ]


def test_alternate_valid_parameters_produce_a_meaningfully_different_mesh():
    default_response = handle_request(_request(command="preview"))
    alternate_response = handle_request(
        _request(command="preview", parameters=_params({"body_width": 60.0}))
    )

    assert alternate_response["ok"] is True
    default_bounds = default_response["result"]["bounds"]
    alternate_bounds = alternate_response["result"]["bounds"]
    # Widening body_width must widen the X extent of the generated bounds —
    # a real, attributable geometry change, not merely "request succeeded".
    default_x_extent = default_bounds["max"][0] - default_bounds["min"][0]
    alternate_x_extent = alternate_bounds["max"][0] - alternate_bounds["min"][0]
    assert alternate_x_extent > default_x_extent


def test_preview_without_parameters_schema_key_still_uses_defaults():
    # {} (falsy) preserves the exact Build 022 parameterless-preview shape.
    response = handle_request(_request(command="preview", parameters={}))
    assert response["ok"] is True


def test_preview_rejects_wrong_parameters_schema():
    response = handle_request(
        _request(command="preview", parameters={"schema": "not-a-real-schema", "values": {}})
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameters_schema"


def test_preview_rejects_non_object_values():
    response = handle_request(
        _request(command="preview", parameters={"schema": PARAMETERS_SCHEMA, "values": "nope"})
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameters"


def test_preview_rejects_unknown_field_name():
    response = handle_request(
        _request(command="preview", parameters=_params({"not_a_real_field": 1.0}))
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameters"


def test_preview_rejects_wrong_field_type():
    response = handle_request(
        _request(command="preview", parameters=_params({"body_width": "wide"}))
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameter_type"
    assert response["error"]["details"]["field"] == "body_width"


def test_preview_rejects_out_of_range_value():
    response = handle_request(_request(command="preview", parameters=_params({"body_width": -1.0})))
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameters_domain"


def test_preview_rejects_invalid_cross_parameter_combination():
    response = handle_request(
        _request(
            command="preview",
            parameters=_params({"groove_diameter": 5.0, "rod_diameter": 3.0}),
        )
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameters_domain"
    assert "errors" in response["error"]["details"]


def test_valid_then_invalid_then_valid_sequence_all_succeed_independently():
    good_1 = handle_request(_request(command="preview"))
    bad = handle_request(_request(command="preview", parameters=_params({"body_width": -1.0})))
    good_2 = handle_request(_request(command="preview"))

    assert good_1["ok"] is True
    assert bad["ok"] is False
    assert good_2["ok"] is True


def test_parameters_error_response_never_contains_traceback_text():
    response = handle_request(
        _request(command="preview", parameters=_params({"body_width": "wide"}))
    )
    serialized = json.dumps(response)
    assert "Traceback" not in serialized
    assert 'File "' not in serialized
