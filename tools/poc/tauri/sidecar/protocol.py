"""zerorod-sidecar/v1 request/response envelope (TE-002 section 11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SIDECAR_SCHEMA = "zerorod-sidecar/v1"


class SidecarError(Exception):
    """Raised for any handled, reportable failure. Carries a stable error code
    and a message safe to forward to the frontend — never a raw traceback."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Request:
    request_id: str
    command: str
    parameters: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Request:
        if not isinstance(data, dict):
            raise SidecarError("invalid_request", "request must be a JSON object")
        if data.get("schema") != SIDECAR_SCHEMA:
            raise SidecarError(
                "invalid_schema",
                f"expected schema '{SIDECAR_SCHEMA}', got {data.get('schema')!r}",
            )
        request_id = data.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise SidecarError("invalid_request", "request_id must be a non-empty string")
        command = data.get("command")
        if not isinstance(command, str) or not command:
            raise SidecarError("invalid_request", "command must be a non-empty string")
        parameters = data.get("parameters", {})
        if not isinstance(parameters, dict):
            raise SidecarError("invalid_request", "parameters must be a JSON object")
        return cls(request_id=request_id, command=command, parameters=parameters)


def ok_response(request_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SIDECAR_SCHEMA,
        "request_id": request_id,
        "ok": True,
        "result": result,
    }


def error_response(request_id: str | None, code: str, message: str) -> dict[str, Any]:
    return {
        "schema": SIDECAR_SCHEMA,
        "request_id": request_id,
        "ok": False,
        "error": {"code": code, "message": message},
    }
