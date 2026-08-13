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


def _run_export_command(parameters: dict) -> dict:
    """Build 024 M1 — exposes the existing, unmodified
    `zerorodcad.export.export_project` through the sidecar boundary.

    Request shape (nested under the outer envelope's `parameters`):
        {
          "parameters": {"schema": "zerorod-parameters/v1", "values": {...}},
          "output_directory": "<user-selected absolute path>"
        }

    `parameters.parameters` reuses `parse_parameters_request` unmodified — an
    empty/omitted object still resolves to canonical defaults, exactly like
    `preview`. `output_directory` is new surface specific to `export`: it
    crosses the boundary as a plain string chosen by the user through the
    Rust-owned native directory dialog (see commands.rs) — this handler only
    ever writes to the path it is given, never lists or browses a directory.
    """
    from zerorod_sidecar.parameters_contract import parse_parameters_request
    from zerorodcad.export import export_project
    from zerorodcad.validation import validate_parameters

    output_directory = parameters.get("output_directory")
    if not isinstance(output_directory, str) or not output_directory.strip():
        raise SidecarError(
            "invalid_destination",
            "output_directory must be a non-empty string",
            details={"field": "output_directory"},
        )

    # Level 1/2: identical parsing path to `preview` — no second parser.
    params = parse_parameters_request(parameters.get("parameters", {}))

    # Level 3: same domain validator `preview` uses. `export_project` itself
    # re-validates internally (existing engine behavior, unchanged) — this
    # earlier check exists so a domain-invalid request fails with the same
    # structured `invalid_parameters_domain` shape `preview` already uses,
    # rather than surfacing as a generic `export_failed`.
    validation = validate_parameters(params)
    if not validation.is_valid:
        raise SidecarError(
            "invalid_parameters_domain",
            "; ".join(validation.errors),
            details={"errors": list(validation.errors)},
        )

    export_started = time.perf_counter()
    try:
        body_path, assembly_path, report_path = export_project(output_directory, params)
    except FileExistsError as exc:
        raise SidecarError(
            "export_invalid_destination",
            f"export destination is not usable: {exc}",
        ) from exc
    except PermissionError as exc:
        raise SidecarError(
            "export_permission_denied",
            f"permission denied writing to export destination: {exc}",
        ) from exc
    except OSError as exc:
        raise SidecarError(
            "export_write_failed",
            f"export destination could not be written: {exc}",
        ) from exc
    except ValueError as exc:
        # export_project's own internal validate_parameters re-check
        # (defense in depth in the engine, not duplicated here) — reached
        # only if Level 3 above somehow disagreed with it.
        raise SidecarError("invalid_parameters_domain", str(exc)) from exc
    except Exception as exc:
        raise SidecarError(
            "export_failed",
            f"export failed: {type(exc).__name__}: {exc}",
        ) from exc
    export_duration = time.perf_counter() - export_started

    # Empirically (Build 024 M1 discovery), CadQuery's STL/STEP exporters can
    # silently no-op into a directory they cannot actually write to (no
    # exception, no file) even though a plain Python file write
    # (`report.md`) correctly raises `PermissionError` for the same
    # directory. `export_project` is therefore not trusted to have written
    # everything just because it returned without raising — every expected
    # output is verified to actually exist and be non-empty before this
    # handler reports success.
    named_outputs = (
        ("body_stl", body_path),
        ("assembly_step", assembly_path),
        ("report_markdown", report_path),
    )
    missing = [
        role for role, path in named_outputs if not path.is_file() or path.stat().st_size == 0
    ]
    if missing:
        raise SidecarError(
            "export_incomplete",
            "export reported success but did not produce all expected output files: "
            + ", ".join(missing),
            details={"missing": missing},
        )

    return {
        "output_directory": str(Path(output_directory)),
        "files": [
            {"role": role, "filename": path.name, "path": str(path)} for role, path in named_outputs
        ],
        "timing": {"export_seconds": export_duration},
    }


def _run_export_preflight_command(parameters: dict) -> dict:
    """Build 024 M2 — pure, side-effect-free conflict check: which of
    `export`'s expected output filenames already exist in `output_directory`.

    Performs no export and no directory listing/enumeration; it only checks
    the fixed, known set of filenames `export_project` would itself produce
    (via `zerorodcad.export.expected_output_filenames`, the same
    sanitization logic `export` uses, reused rather than duplicated — see
    docs/migration/BUILD-024-M1-EXPORT-FOUNDATION.md's `project_name`
    findings). Same request shape as `export` (minus performing the export
    itself), so the frontend can preflight with the exact same accepted
    parameters/destination it would otherwise export with.
    """
    from zerorod_sidecar.parameters_contract import parse_parameters_request
    from zerorodcad.export import expected_output_filenames

    output_directory = parameters.get("output_directory")
    if not isinstance(output_directory, str) or not output_directory.strip():
        raise SidecarError(
            "invalid_destination",
            "output_directory must be a non-empty string",
            details={"field": "output_directory"},
        )

    # Level 1/2 only: this is a filename check, not an export — no domain
    # (Level 3) validation is needed just to read `project_name` back out.
    params = parse_parameters_request(parameters.get("parameters", {}))
    expected = expected_output_filenames(params.project_name)

    directory = Path(output_directory)
    expected_files = [{"role": role, "filename": filename} for role, filename in expected.items()]
    conflicts = [entry for entry in expected_files if (directory / entry["filename"]).is_file()]

    return {
        "output_directory": str(directory),
        "expected_files": expected_files,
        "conflicts": conflicts,
        "has_conflicts": bool(conflicts),
    }


def _run_project_open_command(parameters: dict) -> dict:
    """Build 025 M1 — exposes the existing, unmodified
    `zerorodcad.project.load_project` through the sidecar boundary.

    Request shape: {"path": "<absolute .zerorod path>"}. `path` crosses the
    boundary as a plain string obtained from the Rust-owned native open
    dialog (see commands.rs) — this handler only ever reads the path it is
    given, never lists or browses a directory.

    Re-validates the loaded parameters (Level 3, the same
    `zerorodcad.validation.validate_parameters` `preview`/`export` already
    use) before returning — a `.zerorod` file did not necessarily come from
    this app's own Save (it could be hand-edited), so a domain-invalid file
    must fail here, atomically, rather than reach the frontend as a
    committed project state (docs/migration/BUILD-025-M1-PROJECT-PERSISTENCE.md
    "Open must be atomic").
    """
    from zerorod_sidecar.parameters_contract import parameters_to_contract
    from zerorodcad.project import load_project
    from zerorodcad.validation import validate_parameters

    path = parameters.get("path")
    if not isinstance(path, str) or not path.strip():
        raise SidecarError(
            "invalid_request",
            "path must be a non-empty string",
            details={"field": "path"},
        )

    target = Path(path)
    if not target.is_file():
        raise SidecarError("project_not_found", f"project file not found: {path}")

    try:
        params = load_project(target)
    except PermissionError as exc:
        raise SidecarError(
            "project_permission_denied",
            f"permission denied reading project file: {exc}",
        ) from exc
    except OSError as exc:
        raise SidecarError(
            "project_read_failed",
            f"project file could not be read: {exc}",
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Unsupported project version"):
            raise SidecarError("project_version_unsupported", message) from exc
        raise SidecarError("project_invalid", message) from exc
    except (AttributeError, TypeError, KeyError) as exc:
        # project.py has no dedicated guard for well-formed-JSON-but-wrong-
        # shape payloads (e.g. a top-level JSON array/string/number, or a
        # missing "parameters" key) — reused unmodified (§4), so this call
        # site maps that class of failure the same as any other
        # structurally-invalid project file rather than letting it surface
        # as an unhandled internal_error.
        raise SidecarError(
            "project_invalid",
            f"project file is not a valid ZeroRodCAD project: {exc}",
        ) from exc

    validation = validate_parameters(params)
    if not validation.is_valid:
        raise SidecarError(
            "invalid_parameters_domain",
            "; ".join(validation.errors),
            details={"errors": list(validation.errors)},
        )

    return parameters_to_contract(params)


def _run_project_save_command(parameters: dict) -> dict:
    """Build 025 M1 — exposes the existing, unmodified
    `zerorodcad.project.save_project` through the sidecar boundary.

    Request shape (nested under the outer envelope's `parameters`):
        {
          "parameters": {"schema": "zerorod-parameters/v1", "values": {...}},
          "path": "<user-selected absolute destination path>"
        }

    `parameters.parameters` reuses `parse_parameters_request` unmodified —
    the same Level 1/2 parsing `preview`/`export` already use. `path` is new
    surface specific to `project_save`: a plain string chosen by the user
    through the Rust-owned native save dialog (see commands.rs); this
    handler only ever writes to the path it is given.
    """
    from zerorod_sidecar.parameters_contract import parameters_to_contract, parse_parameters_request
    from zerorodcad.project import save_project
    from zerorodcad.validation import validate_parameters

    path = parameters.get("path")
    if not isinstance(path, str) or not path.strip():
        raise SidecarError(
            "invalid_request",
            "path must be a non-empty string",
            details={"field": "path"},
        )

    # Level 1/2: identical parsing path to preview/export — no second parser.
    params = parse_parameters_request(parameters.get("parameters", {}))

    # Level 3: defense in depth. The frontend only ever submits `accepted`
    # (already engine-validated) state (docs/migration/
    # BUILD-025-M1-PROJECT-PERSISTENCE.md "Canonical Save State"), but this
    # handler never trusts that blindly — mirrors `export`'s own re-check.
    validation = validate_parameters(params)
    if not validation.is_valid:
        raise SidecarError(
            "invalid_parameters_domain",
            "; ".join(validation.errors),
            details={"errors": list(validation.errors)},
        )

    try:
        written_path = save_project(path, params)
    except PermissionError as exc:
        raise SidecarError(
            "project_permission_denied",
            f"permission denied writing project file: {exc}",
        ) from exc
    except OSError as exc:
        raise SidecarError(
            "project_write_failed",
            f"project file could not be written: {exc}",
        ) from exc

    return {"path": str(written_path), "parameters": parameters_to_contract(params)}


def _run_report_command(parameters: dict) -> dict:
    """Build 025 M3 — the Instrument Report (§16-23 of the mandate): exposes
    the existing, unmodified `zerorodcad.report.build_report` (already the
    sole source `zerorodcad.export.save_report`/the legacy PySide6 app's
    "Instrument Report" tab both use — this command does not create a
    second report implementation, it is the third caller of the same one)
    through the sidecar boundary. Request shape mirrors `preview`'s: the
    outer `parameters` object IS directly a zerorod-parameters/v1 request
    (no nested `output_directory`-style wrapper — a report has nowhere to
    write). Same Level 1-3 validation as `preview` (structural/type parsing
    via `parse_parameters_request`, then the one existing domain validator)
    — a report is never built for a domain-invalid parameter set, mirroring
    `preview`'s own behavior; no CadQuery geometry construction happens
    here at all (`build_report` only reads `ZeroRodParameters` fields/
    properties), so this is cheaper than `preview`, not a second version of
    it.
    """
    from zerorod_sidecar.parameters_contract import parse_parameters_request
    from zerorodcad.report import build_report
    from zerorodcad.validation import validate_parameters

    params = parse_parameters_request(parameters)

    validation = validate_parameters(params)
    if not validation.is_valid:
        raise SidecarError(
            "invalid_parameters_domain",
            "; ".join(validation.errors),
            details={"errors": list(validation.errors)},
        )

    return {"markdown": build_report(params)}


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
    "report": _run_report_command,
    "export": _run_export_command,
    "export_preflight": _run_export_preflight_command,
    "parameters_defaults": _run_parameters_defaults_command,
    "project_open": _run_project_open_command,
    "project_save": _run_project_save_command,
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
