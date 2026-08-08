"""TE-002 sidecar entry point.

Protocol: read exactly one JSON request line from stdin, write exactly one
JSON response line to stdout, then exit. This shape is deliberate — Tauri's
shell-plugin Child.write() cannot close a sidecar's stdin (no EOF signal is
available), so the sidecar must never block on a stdin read-to-EOF; reading
one newline-terminated line is the only reliable option.

All diagnostics/tracebacks go to stderr only. stdout carries nothing but the
single JSON response line, so a Tauri-side JSON parse of stdout can never be
corrupted by log output.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# VTKImportBlocker must be installed before the first cadquery import, per
# TE-001 section 11. Reused verbatim — no second VTK-blocking mechanism.
from tools.poc.novtk.vtk_import_blocker import install as install_vtk_blocker  # noqa: E402
from tools.poc.tauri.sidecar.protocol import (  # noqa: E402
    Request,
    SidecarError,
    error_response,
    ok_response,
)


def _run_preview_command(parameters: dict) -> dict:
    from tools.poc.tauri.sidecar.mesh_contract import scene_to_mesh_contract, validate_mesh_contract

    if parameters:
        raise SidecarError(
            "unsupported_parameters",
            "the 'preview' command only supports default ZeroRod parameters in TE-002",
        )

    from zerorodcad.parameters import default_parameters
    from zerorodcad.preview import build_preview_scene

    build_started = time.perf_counter()
    params = default_parameters()
    scene = build_preview_scene(params)
    build_duration = time.perf_counter() - build_started

    serialize_started = time.perf_counter()
    payload = scene_to_mesh_contract(scene)
    serialize_duration = time.perf_counter() - serialize_started

    problems = validate_mesh_contract(payload)
    if problems:
        raise SidecarError(
            "invalid_mesh",
            "generated mesh failed validation: " + "; ".join(problems),
        )

    payload["timing"] = {
        "model_and_tessellation_seconds": build_duration,
        "serialization_seconds": serialize_duration,
    }
    return payload


COMMANDS = {
    "preview": _run_preview_command,
}


def handle_request(raw_line: str) -> dict:
    request_id: str | None = None
    try:
        data = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        return error_response(None, "invalid_json", f"could not parse request JSON: {exc}")

    try:
        request = Request.from_dict(data)
        request_id = request.request_id
        handler = COMMANDS.get(request.command)
        if handler is None:
            raise SidecarError("unknown_command", f"unknown command: {request.command!r}")
        result = handler(request.parameters)
        return ok_response(request.request_id, result)
    except SidecarError as exc:
        return error_response(request_id, exc.code, exc.message)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see module docstring
        traceback.print_exc(file=sys.stderr)
        return error_response(request_id, "internal_error", f"{type(exc).__name__}: {exc}")


def main() -> int:
    install_vtk_blocker()

    raw_line = sys.stdin.readline()
    if not raw_line:
        response = error_response(None, "empty_request", "no request received on stdin")
    else:
        response = handle_request(raw_line)

    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
