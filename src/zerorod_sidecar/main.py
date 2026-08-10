"""Build 022 M2 productive sidecar entry point.

Persistent only (docs/adr/ADR-022-001-DESKTOP-2-0-TAURI-ARCHITECTURE.md's
"Sidecar runtime strategy": persistent + onedir, no onefile/one-shot
fallback in the productive path — unlike tools/poc/tauri/sidecar/main.py,
which kept a one-shot mode for TE-002/TE-002.1's own comparison). Reads JSON
request lines from stdin in a loop, writes one JSON response line per
request to stdout, until an explicit `shutdown` command or stdin EOF. All
diagnostics/tracebacks go to stderr only.
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# VTKImportBlocker must be installed before the first cadquery import
# (TE-001). Reused verbatim as a safety net proving no accidental VTK import
# ever silently succeeds in the productive sidecar — not a new mechanism,
# see ADR-022-001 section 23 / docs/migration/BUILD-022-TAURI-DESKTOP-FOUNDATION.md.
from tools.poc.novtk.vtk_import_blocker import install as install_vtk_blocker  # noqa: E402

from zerorod_sidecar.protocol import (  # noqa: E402
    Request,
    SidecarError,
    error_response,
    ok_response,
)

MILESTONE = "build023-m1"


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _run_ping_command(parameters: dict) -> dict:  # noqa: ARG001 - uniform handler signature
    return {"status": "ok", "pid": os.getpid()}


def _run_status_command(parameters: dict) -> dict:  # noqa: ARG001
    cadquery_version = _package_version("cadquery")
    ocp_variant = (
        "cadquery-ocp-novtk"
        if _package_version("cadquery-ocp-novtk")
        else ("cadquery-ocp" if _package_version("cadquery-ocp") else None)
    )
    return {
        "status": "ready",
        "pid": os.getpid(),
        "python_version": platform.python_version(),
        "cadquery_version": cadquery_version,
        "ocp_variant": ocp_variant,
        "vtk_installed": _package_version("vtk") is not None,
        "milestone": MILESTONE,
    }


def _run_preview_command(parameters: dict) -> dict:
    from zerorod_sidecar.mesh_contract import scene_to_mesh_contract, validate_mesh_contract
    from zerorod_sidecar.parameters_contract import parse_parameters_request
    from zerorodcad.preview import build_preview_scene
    from zerorodcad.validation import validate_parameters

    # Level 1 (structural) / Level 2 (per-field type): zerorod-parameters/v1
    # parsing. An empty `parameters` object still resolves to the canonical
    # defaults — the Build 022 parameterless preview path is unchanged.
    params = parse_parameters_request(parameters)

    # Level 3 (cross-parameter/domain): the single existing engine-owned
    # validator, reused unmodified (docs/contracts/ZEROROD-PARAMETERS-V1.md).
    validation = validate_parameters(params)
    if not validation.is_valid:
        raise SidecarError(
            "invalid_parameters_domain",
            "; ".join(validation.errors),
            details={"errors": list(validation.errors)},
        )

    build_started = time.perf_counter()
    try:
        # Level 4: a validated parameter set can still fail at actual
        # geometry construction — distinguished from other internal errors
        # so the frontend can tell "bad input" from "engine defect" apart.
        scene = build_preview_scene(params)
    except Exception as exc:
        raise SidecarError(
            "geometry_error",
            f"geometry generation failed: {type(exc).__name__}: {exc}",
        ) from exc
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


def _run_parameters_defaults_command(parameters: dict) -> dict:  # noqa: ARG001
    """Returns the canonical default ZeroRodParameters wrapped in the
    zerorod-parameters/v1 envelope — the single authoritative default set a
    future frontend can consume instead of hardcoding a second copy."""
    from zerorod_sidecar.parameters_contract import parameters_to_contract
    from zerorodcad.parameters import default_parameters

    return parameters_to_contract(default_parameters())


def _run_shutdown_command(parameters: dict) -> dict:  # noqa: ARG001
    return {"status": "shutting_down", "pid": os.getpid()}


COMMANDS = {
    "ping": _run_ping_command,
    "status": _run_status_command,
    "preview": _run_preview_command,
    "parameters_defaults": _run_parameters_defaults_command,
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
        return error_response(request_id, exc.code, exc.message, exc.details)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, never raise raw tracebacks to stdout
        traceback.print_exc(file=sys.stderr)
        return error_response(request_id, "internal_error", f"{type(exc).__name__}: {exc}")


def _write_response(response: dict) -> None:
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def run_persistent() -> int:
    """Loop until `shutdown` or stdin EOF. A malformed/erroring request does
    NOT terminate the process — handle_request's per-line error isolation is
    what keeps the loop alive across bad input."""
    while True:
        raw_line = sys.stdin.readline()
        if not raw_line:
            # stdin EOF: treated as an implicit shutdown, not an error — the
            # Rust engine manager closing stdin is a normal cleanup path.
            return 0
        stripped = raw_line.strip()
        if not stripped:
            continue

        response = handle_request(raw_line)
        _write_response(response)

        try:
            command = json.loads(raw_line).get("command")
        except json.JSONDecodeError:
            command = None
        if command == "shutdown":
            return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ZeroRodCAD Desktop 2.0 productive sidecar")
    parser.add_argument(
        "--persistent",
        action="store_true",
        help=(
            "Accepted for compatibility with tools/poc/tauri/benchmark_sidecar_runtime.py, "
            "which always passes it. The productive sidecar is persistent-only regardless "
            "(ADR-022-001) — this flag does not change behavior."
        ),
    )
    parser.parse_args(argv)

    install_vtk_blocker()
    return run_persistent()


if __name__ == "__main__":
    raise SystemExit(main())
