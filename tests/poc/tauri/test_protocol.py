"""Tests for the zerorod-sidecar/v1 request/response envelope (TE-002 section 29)."""

from __future__ import annotations

import pytest
from tools.poc.tauri.sidecar.protocol import (
    SIDECAR_SCHEMA,
    Request,
    SidecarError,
    error_response,
    ok_response,
)


def test_valid_request_parses():
    request = Request.from_dict(
        {"schema": SIDECAR_SCHEMA, "request_id": "abc123", "command": "preview", "parameters": {}}
    )
    assert request.request_id == "abc123"
    assert request.command == "preview"
    assert request.parameters == {}


def test_missing_schema_rejected():
    with pytest.raises(SidecarError) as excinfo:
        Request.from_dict({"request_id": "x", "command": "preview"})
    assert excinfo.value.code == "invalid_schema"


def test_wrong_schema_rejected():
    with pytest.raises(SidecarError) as excinfo:
        Request.from_dict({"schema": "not-the-schema", "request_id": "x", "command": "preview"})
    assert excinfo.value.code == "invalid_schema"


def test_missing_request_id_rejected():
    with pytest.raises(SidecarError) as excinfo:
        Request.from_dict({"schema": SIDECAR_SCHEMA, "command": "preview"})
    assert excinfo.value.code == "invalid_request"


def test_missing_command_rejected():
    with pytest.raises(SidecarError) as excinfo:
        Request.from_dict({"schema": SIDECAR_SCHEMA, "request_id": "x"})
    assert excinfo.value.code == "invalid_request"


def test_non_dict_parameters_rejected():
    with pytest.raises(SidecarError) as excinfo:
        Request.from_dict(
            {
                "schema": SIDECAR_SCHEMA,
                "request_id": "x",
                "command": "preview",
                "parameters": [1, 2],
            }
        )
    assert excinfo.value.code == "invalid_request"


def test_non_dict_request_rejected():
    with pytest.raises(SidecarError) as excinfo:
        Request.from_dict("not a dict")  # type: ignore[arg-type]
    assert excinfo.value.code == "invalid_request"


def test_default_parameters_when_absent():
    request = Request.from_dict({"schema": SIDECAR_SCHEMA, "request_id": "x", "command": "preview"})
    assert request.parameters == {}


def test_ok_response_shape():
    response = ok_response("rid", {"foo": "bar"})
    assert response == {
        "schema": SIDECAR_SCHEMA,
        "request_id": "rid",
        "ok": True,
        "result": {"foo": "bar"},
    }


def test_error_response_shape():
    response = error_response("rid", "some_code", "some message")
    assert response == {
        "schema": SIDECAR_SCHEMA,
        "request_id": "rid",
        "ok": False,
        "error": {"code": "some_code", "message": "some message"},
    }


def test_error_response_allows_null_request_id():
    response = error_response(None, "invalid_json", "bad")
    assert response["request_id"] is None
