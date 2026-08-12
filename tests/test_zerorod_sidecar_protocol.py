"""Tests for zerorod_sidecar.protocol's zerorod-sidecar/v1 envelope (Build 022 M2)."""

from __future__ import annotations

from zerorod_sidecar.protocol import (
    SIDECAR_SCHEMA,
    Request,
    SidecarError,
    error_response,
    ok_response,
)


def test_schema_constant_matches_the_versioned_contract_name():
    assert SIDECAR_SCHEMA == "zerorod-sidecar/v1"


def test_request_from_dict_accepts_a_well_formed_request():
    request = Request.from_dict(
        {"schema": SIDECAR_SCHEMA, "request_id": "r1", "command": "ping", "parameters": {}}
    )
    assert request.request_id == "r1"
    assert request.command == "ping"
    assert request.parameters == {}


def test_request_from_dict_defaults_missing_parameters_to_empty_dict():
    request = Request.from_dict({"schema": SIDECAR_SCHEMA, "request_id": "r1", "command": "ping"})
    assert request.parameters == {}


def test_request_from_dict_rejects_non_dict_payload():
    try:
        Request.from_dict("not a dict")  # type: ignore[arg-type]
        raise AssertionError("expected SidecarError")
    except SidecarError as exc:
        assert exc.code == "invalid_request"


def test_request_from_dict_rejects_wrong_schema():
    try:
        Request.from_dict({"schema": "wrong", "request_id": "r1", "command": "ping"})
        raise AssertionError("expected SidecarError")
    except SidecarError as exc:
        assert exc.code == "invalid_schema"


def test_request_from_dict_rejects_empty_request_id():
    try:
        Request.from_dict({"schema": SIDECAR_SCHEMA, "request_id": "", "command": "ping"})
        raise AssertionError("expected SidecarError")
    except SidecarError as exc:
        assert exc.code == "invalid_request"


def test_request_from_dict_rejects_non_string_command():
    try:
        Request.from_dict({"schema": SIDECAR_SCHEMA, "request_id": "r1", "command": 5})
        raise AssertionError("expected SidecarError")
    except SidecarError as exc:
        assert exc.code == "invalid_request"


def test_request_from_dict_rejects_non_dict_parameters():
    try:
        Request.from_dict(
            {"schema": SIDECAR_SCHEMA, "request_id": "r1", "command": "ping", "parameters": []}
        )
        raise AssertionError("expected SidecarError")
    except SidecarError as exc:
        assert exc.code == "invalid_request"


def test_ok_response_has_expected_shape():
    response = ok_response("r1", {"status": "ok"})
    assert response == {
        "schema": SIDECAR_SCHEMA,
        "request_id": "r1",
        "ok": True,
        "result": {"status": "ok"},
    }


def test_error_response_has_expected_shape():
    response = error_response("r1", "unknown_command", "nope")
    assert response == {
        "schema": SIDECAR_SCHEMA,
        "request_id": "r1",
        "ok": False,
        "error": {"code": "unknown_command", "message": "nope"},
    }


def test_error_response_allows_none_request_id():
    response = error_response(None, "invalid_json", "bad json")
    assert response["request_id"] is None
