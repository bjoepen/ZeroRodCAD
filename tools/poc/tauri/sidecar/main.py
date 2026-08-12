"""TE-002 / TE-002.1 sidecar entry point.

Two transport modes over the *same* zerorod-sidecar/v1 request/response
content contract (TE-002.1 section 7: reuse the same content, don't fork the
schema):

- **one-shot** (default, unchanged from TE-002): read exactly one JSON
  request line from stdin, write exactly one JSON response line to stdout,
  then exit. Required because Tauri's shell-plugin Child.write() cannot
  close a sidecar's stdin (no EOF signal available).
- **persistent** (``--persistent`` flag, TE-002.1 Variant C): read JSON
  request lines in a loop, write one JSON response line per request, until
  an explicit ``shutdown`` command or stdin EOF. Every response line is
  still exactly one JSON object; stdout never carries anything else.

All diagnostics/tracebacks go to stderr only, in both modes.
"""

from __future__ import annotations

import argparse
import json
import os
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


def _run_ping_command(parameters: dict) -> dict:  # noqa: ARG001 - uniform handler signature
    return {"status": "ok", "pid": os.getpid()}


def _run_shutdown_command(parameters: dict) -> dict:  # noqa: ARG001
    return {"status": "shutting_down", "pid": os.getpid()}


COMMANDS = {
    "preview": _run_preview_command,
    "ping": _run_ping_command,
    "shutdown": _run_shutdown_command,
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


def _write_response(response: dict) -> None:
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def run_one_shot() -> int:
    """TE-002 original behavior, byte-for-byte unchanged."""
    raw_line = sys.stdin.readline()
    if not raw_line:
        response = error_response(None, "empty_request", "no request received on stdin")
    else:
        response = handle_request(raw_line)
    _write_response(response)
    return 0


def run_persistent() -> int:
    """TE-002.1 Variant C: loop until `shutdown` or stdin EOF (section 14).

    A malformed/erroring request does NOT terminate the process — the same
    error-isolation `handle_request` already provides per-line is exactly
    what keeps the loop alive across bad input (section 40: "Ein
    fehlerhafter Request darf den persistenten Prozess nicht zwingend
    zerstören").
    """
    while True:
        raw_line = sys.stdin.readline()
        if not raw_line:
            # stdin EOF: treated as an implicit shutdown, not an error —
            # this is exactly the "Rust closes stdin" cleanup path.
            return 0
        stripped = raw_line.strip()
        if not stripped:
            continue

        response = handle_request(raw_line)
        _write_response(response)

        # A well-formed shutdown request always ends the loop after its
        # response is sent, whether it succeeded or was itself malformed
        # enough to fail validation (still safe to stop on request).
        try:
            command = json.loads(raw_line).get("command")
        except json.JSONDecodeError:
            command = None
        if command == "shutdown":
            return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TE-002/TE-002.1 ZeroRodCAD sidecar")
    parser.add_argument(
        "--persistent",
        action="store_true",
        help="TE-002.1 Variant C: serve multiple requests over one process lifetime",
    )
    args = parser.parse_args(argv)

    install_vtk_blocker()

    if args.persistent:
        return run_persistent()
    return run_one_shot()


if __name__ == "__main__":
    raise SystemExit(main())
