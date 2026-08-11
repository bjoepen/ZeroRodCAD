"""Tests for zerorod_sidecar.main's request dispatch (Build 022 M2, extended
for zerorod-parameters/v1 in Build 023 M1)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

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


# --- Build 024 M1: export -----------------------------------------------


def _export_request(output_directory: str, values: dict | None = None) -> str:
    parameters: dict = {"output_directory": output_directory}
    if values is not None:
        parameters["parameters"] = _params(values)
    return _request(command="export", parameters=parameters)


def test_export_with_canonical_defaults_produces_expected_output_inventory(tmp_path: Path) -> None:
    response = handle_request(_export_request(str(tmp_path)))
    assert response["ok"] is True
    result = response["result"]
    assert result["output_directory"] == str(tmp_path)
    roles = {f["role"] for f in result["files"]}
    assert roles == {"body_stl", "assembly_step", "report_markdown"}
    for entry in result["files"]:
        path = Path(entry["path"])
        assert path.is_file()
        assert path.stat().st_size > 0
        assert entry["filename"].startswith("cbg-open-g-")
    assert "timing" in result
    assert result["timing"]["export_seconds"] >= 0


def test_export_result_is_json_serializable_and_has_no_traceback(tmp_path: Path) -> None:
    response = handle_request(_export_request(str(tmp_path)))
    serialized = json.dumps(response)
    assert "Traceback" not in serialized
    assert 'File "' not in serialized


def test_export_alternate_parameters_produce_different_geometry(tmp_path: Path) -> None:
    default_dir = tmp_path / "default"
    alt_dir = tmp_path / "alt"
    default_dir.mkdir()
    alt_dir.mkdir()

    handle_request(_export_request(str(default_dir)))
    handle_request(_export_request(str(alt_dir), {"body_width": 60.0}))

    default_stl = (default_dir / "cbg-open-g-body.stl").read_bytes()
    alt_stl = (alt_dir / "cbg-open-g-body.stl").read_bytes()
    assert default_stl != alt_stl

    default_report = (default_dir / "cbg-open-g-report.md").read_text()
    alt_report = (alt_dir / "cbg-open-g-report.md").read_text()
    assert "38.00 mm" in default_report
    assert "60.00 mm" in alt_report


def test_export_project_name_shapes_generated_filenames(tmp_path: Path) -> None:
    response = handle_request(_export_request(str(tmp_path), {"project_name": "My Custom Rod!"}))
    assert response["ok"] is True
    filenames = {f["filename"] for f in response["result"]["files"]}
    assert filenames == {
        "my-custom-rod-body.stl",
        "my-custom-rod-assembly.step",
        "my-custom-rod-report.md",
    }


def test_export_missing_output_directory_returns_invalid_destination_error() -> None:
    response = handle_request(_request(command="export", parameters={}))
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_destination"


def test_export_empty_output_directory_returns_invalid_destination_error() -> None:
    response = handle_request(_request(command="export", parameters={"output_directory": "   "}))
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_destination"


def test_export_rejects_invalid_domain_parameters(tmp_path: Path) -> None:
    response = handle_request(
        _export_request(str(tmp_path), {"groove_diameter": 5.0, "rod_diameter": 3.0})
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameters_domain"
    assert "errors" in response["error"]["details"]
    # Build 024 M3 §22: validation happens before export_project is ever
    # called — no partial/stray output may exist for a rejected request.
    assert list(tmp_path.iterdir()) == []


def test_export_rejects_wrong_field_type(tmp_path: Path) -> None:
    response = handle_request(_export_request(str(tmp_path), {"body_width": "wide"}))
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameter_type"


def test_export_destination_that_is_an_existing_file_returns_error(tmp_path: Path) -> None:
    conflicting_file = tmp_path / "not-a-directory"
    conflicting_file.write_text("x")
    response = handle_request(_export_request(str(conflicting_file)))
    assert response["ok"] is False
    assert response["error"]["code"] == "export_invalid_destination"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits only")
def test_export_permission_denied_directory_returns_structured_error(tmp_path: Path) -> None:
    read_only_dir = tmp_path / "readonly"
    read_only_dir.mkdir()
    read_only_dir.chmod(0o500)
    try:
        response = handle_request(_export_request(str(read_only_dir)))
    finally:
        read_only_dir.chmod(0o700)
    assert response["ok"] is False
    # CadQuery's STL/STEP exporters can silently no-op on an unwritable
    # directory (Build 024 M1 discovery) rather than raising PermissionError
    # themselves — export_incomplete is the backstop that catches that case;
    # export_permission_denied is the direct-raise case (e.g. the plain
    # Python report.md write). Either is an acceptable structured outcome
    # here, unlike an unhandled exception or a false "ok": true.
    assert response["error"]["code"] in {"export_permission_denied", "export_incomplete"}


def test_export_overwrites_existing_output_files_in_place(tmp_path: Path) -> None:
    handle_request(_export_request(str(tmp_path)))
    first_stl_bytes = (tmp_path / "cbg-open-g-body.stl").read_bytes()

    response = handle_request(_export_request(str(tmp_path), {"body_width": 60.0}))
    assert response["ok"] is True

    # Same filenames (same project_name) get overwritten in place, not
    # duplicated alongside the old ones — the new content wins.
    files_in_dir = {p.name for p in tmp_path.iterdir()}
    assert files_in_dir == {
        "cbg-open-g-body.stl",
        "cbg-open-g-assembly.step",
        "cbg-open-g-report.md",
    }
    assert (tmp_path / "cbg-open-g-body.stl").read_bytes() != first_stl_bytes
    assert "60.00 mm" in (tmp_path / "cbg-open-g-report.md").read_text()


def test_export_valid_after_a_failed_export_request(tmp_path: Path) -> None:
    bad_values = {"groove_diameter": 5.0, "rod_diameter": 3.0}
    bad = handle_request(_export_request(str(tmp_path), bad_values))
    good = handle_request(_export_request(str(tmp_path)))
    assert bad["ok"] is False
    assert good["ok"] is True


def test_export_unknown_field_name_rejected(tmp_path: Path) -> None:
    response = handle_request(_export_request(str(tmp_path), {"not_a_real_field": 1.0}))
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_parameters"


# --- Build 024 M2: export_preflight --------------------------------------


def _export_preflight_request(output_directory: str, values: dict | None = None) -> str:
    parameters: dict = {"output_directory": output_directory}
    if values is not None:
        parameters["parameters"] = _params(values)
    return _request(command="export_preflight", parameters=parameters)


def test_export_preflight_no_conflict_in_empty_directory(tmp_path: Path) -> None:
    response = handle_request(_export_preflight_request(str(tmp_path)))
    assert response["ok"] is True
    result = response["result"]
    assert result["output_directory"] == str(tmp_path)
    assert result["has_conflicts"] is False
    assert result["conflicts"] == []
    roles = {f["role"] for f in result["expected_files"]}
    assert roles == {"body_stl", "assembly_step", "report_markdown"}


def test_export_preflight_does_not_perform_an_export(tmp_path: Path) -> None:
    handle_request(_export_preflight_request(str(tmp_path)))
    assert list(tmp_path.iterdir()) == []


def test_export_preflight_reports_one_conflict(tmp_path: Path) -> None:
    handle_request(_export_request(str(tmp_path)))
    response = handle_request(_export_preflight_request(str(tmp_path)))
    result = response["result"]
    assert result["has_conflicts"] is True
    assert len(result["conflicts"]) == 3  # all three real files now exist


def test_export_preflight_reports_multiple_conflicts_partial(tmp_path: Path) -> None:
    (tmp_path / "cbg-open-g-body.stl").write_bytes(b"x")
    (tmp_path / "cbg-open-g-report.md").write_text("x")
    response = handle_request(_export_preflight_request(str(tmp_path)))
    result = response["result"]
    assert result["has_conflicts"] is True
    conflict_roles = {c["role"] for c in result["conflicts"]}
    assert conflict_roles == {"body_stl", "report_markdown"}


def test_export_preflight_sanitized_project_name_collision_detected(tmp_path: Path) -> None:
    # "A!B" and "A?B" both sanitize to "a-b" (documented Build 024 M1
    # finding) — preflight must naturally catch this via the same
    # sanitization export uses, not a separate uniqueness check.
    (tmp_path / "a-b-body.stl").write_bytes(b"x")
    response = handle_request(_export_preflight_request(str(tmp_path), {"project_name": "A?B"}))
    result = response["result"]
    assert result["has_conflicts"] is True
    assert any(c["filename"] == "a-b-body.stl" for c in result["conflicts"])


def test_export_preflight_filenames_match_actual_export_output(tmp_path: Path) -> None:
    preflight = handle_request(
        _export_preflight_request(str(tmp_path), {"project_name": "My Custom Rod!"})
    )["result"]
    export_result = handle_request(
        _export_request(str(tmp_path), {"project_name": "My Custom Rod!"})
    )["result"]

    preflight_filenames = {f["role"]: f["filename"] for f in preflight["expected_files"]}
    export_filenames = {f["role"]: f["filename"] for f in export_result["files"]}
    assert preflight_filenames == export_filenames


def test_export_preflight_missing_output_directory_returns_invalid_destination_error() -> None:
    response = handle_request(_request(command="export_preflight", parameters={}))
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_destination"


def test_export_preflight_empty_output_directory_returns_invalid_destination_error() -> None:
    response = handle_request(
        _request(command="export_preflight", parameters={"output_directory": "   "})
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_destination"


def test_export_preflight_result_is_json_serializable_and_has_no_traceback(tmp_path: Path) -> None:
    response = handle_request(_export_preflight_request(str(tmp_path)))
    serialized = json.dumps(response)
    assert "Traceback" not in serialized
    assert 'File "' not in serialized


# --- Build 024 M3: export robustness & edge cases ------------------------


def test_export_incomplete_when_a_written_output_is_zero_bytes(tmp_path: Path, monkeypatch) -> None:
    """A file that exists but is zero-byte is a distinct failure mode from a
    file that's missing entirely — both must be caught by post-export
    verification (§8/§23 of the M3 mandate). CadQuery cannot reliably be
    forced to produce this outcome at the OS level, so it's simulated via a
    monkeypatched export_project (§41's explicit allowance for failure
    injection that can't safely be reproduced at the OS level)."""

    def fake_export_project(output_directory: str, parameters):
        directory = Path(output_directory)
        directory.mkdir(parents=True, exist_ok=True)
        body_path = directory / "cbg-open-g-body.stl"
        assembly_path = directory / "cbg-open-g-assembly.step"
        report_path = directory / "cbg-open-g-report.md"
        body_path.write_bytes(b"not empty")
        assembly_path.write_bytes(b"")  # zero-byte, simulating a silent no-op
        report_path.write_text("report")
        return body_path, assembly_path, report_path

    monkeypatch.setattr("zerorodcad.export.export_project", fake_export_project)
    response = handle_request(_export_request(str(tmp_path)))
    assert response["ok"] is False
    assert response["error"]["code"] == "export_incomplete"
    assert response["error"]["details"]["missing"] == ["assembly_step"]


def test_export_write_failed_maps_a_simulated_disk_full_oserror(
    tmp_path: Path, monkeypatch
) -> None:
    """§29 of the M3 mandate: real OS-level disk-full is not safely
    testable here without manipulating the real disk — this proves the
    error-mapping path at a controlled write boundary instead, which is
    honestly the limit of what can be verified in this environment
    (classified SIMULATED, not empirically verified against a real full
    disk, in the M3 documentation)."""
    import errno

    def fake_export_project(output_directory: str, parameters):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr("zerorodcad.export.export_project", fake_export_project)
    response = handle_request(_export_request(str(tmp_path)))
    assert response["ok"] is False
    assert response["error"]["code"] == "export_write_failed"
    assert list(tmp_path.iterdir()) == []


def test_export_empty_project_name_falls_back_to_zerorod_end_to_end(tmp_path: Path) -> None:
    """§21 of the M3 mandate: the empty/pathological safe-name case is
    reachable end to end (project_name has no domain validation rule
    rejecting an empty string) and must resolve to the existing engine
    fallback ("zerorod"), not an unusable/empty filename stem — proven
    through the real export pipeline, not just the pure filename helper."""
    response = handle_request(_export_request(str(tmp_path), {"project_name": "   "}))
    assert response["ok"] is True
    filenames = {f["filename"] for f in response["result"]["files"]}
    assert filenames == {"zerorod-body.stl", "zerorod-assembly.step", "zerorod-report.md"}
    for entry in response["result"]["files"]:
        path = Path(entry["path"])
        assert path.is_file() and path.stat().st_size > 0


def test_export_unicode_project_name_succeeds_end_to_end(tmp_path: Path) -> None:
    """§19/§20 of the M3 mandate: a Unicode project name must export
    successfully and produce real, usable, non-ASCII-transliterated
    filenames (documented Build 024 M1 behavior: Unicode letters are kept
    lowercase as-is, not transliterated)."""
    response = handle_request(_export_request(str(tmp_path), {"project_name": "ZeroRod – Prüfung"}))
    assert response["ok"] is True
    filenames = {f["filename"] for f in response["result"]["files"]}
    assert filenames == {
        "zerorod-prüfung-body.stl",
        "zerorod-prüfung-assembly.step",
        "zerorod-prüfung-report.md",
    }
    for entry in response["result"]["files"]:
        path = Path(entry["path"])
        assert path.is_file() and path.stat().st_size > 0


def test_export_into_a_directory_with_spaces_succeeds(tmp_path: Path) -> None:
    """§18 of the M3 mandate: no shell is ever involved in export, so a
    destination directory name containing spaces must work without any
    escaping concern."""
    destination = tmp_path / "ZeroRod Export Test"
    response = handle_request(_export_request(str(destination)))
    assert response["ok"] is True
    for entry in response["result"]["files"]:
        path = Path(entry["path"])
        assert path.is_file() and path.stat().st_size > 0
        assert "ZeroRod Export Test" in str(path)


def test_export_succeeds_even_if_directory_was_removed_after_a_prior_preflight(
    tmp_path: Path,
) -> None:
    """§15 of the M3 mandate ("destination disappears after selection"):
    empirically, this is not actually a failure case — export_project's own
    `mkdir(parents=True, exist_ok=True)` self-heals by recreating the
    directory (documented in Build 024 M1's "Path semantics" already; this
    proves it end to end through the sidecar boundary specifically for the
    "selected via a real preflight, then removed" sequence)."""
    destination = tmp_path / "will-disappear"
    destination.mkdir()
    preflight = handle_request(_export_preflight_request(str(destination)))
    assert preflight["ok"] is True

    destination.rmdir()
    assert not destination.exists()

    response = handle_request(_export_request(str(destination)))
    assert response["ok"] is True
    for entry in response["result"]["files"]:
        path = Path(entry["path"])
        assert path.is_file() and path.stat().st_size > 0


def test_export_repeated_identical_parameters_produce_consistent_output(tmp_path: Path) -> None:
    """Supports the M3 §24-26 retry-safety decision: export_project always
    fully rewrites each output file from scratch (no partial/append writes,
    no cumulative state), so a repeated call with identical parameters can
    never produce a corrupted half-old/half-new file. Empirically, STL
    (pure tessellation) and the Markdown report (a pure text template) are
    fully byte-identical across repeated identical-parameter calls — but
    the STEP assembly export is NOT: CadQuery/OCP's STEP writer assigns
    internal entity IDs and STYLED_ITEM color references in an order that
    is not guaranteed stable across repeated `Assembly.export()` calls in
    the same process (observed directly: identical geometry, but a handful
    of differing NEXT_ASSEMBLY_USAGE_OCCURRENCE/STYLED_ITEM/COLOUR_RGB
    entity lines between two otherwise-identical exports). This is real,
    documented evidence, not assumed — see
    docs/migration/BUILD-024-M3-EXPORT-ROBUSTNESS.md's retry-policy section.
    The STEP file size (not content) is still checked for consistency here,
    since export_project always writes the same shape for the same
    parameters."""
    first = handle_request(_export_request(str(tmp_path)))
    first_files = {entry["role"]: Path(entry["path"]) for entry in first["result"]["files"]}
    stl_bytes_1 = first_files["body_stl"].read_bytes()
    report_text_1 = first_files["report_markdown"].read_text()
    step_size_1 = first_files["assembly_step"].stat().st_size

    second = handle_request(_export_request(str(tmp_path)))
    second_files = {entry["role"]: Path(entry["path"]) for entry in second["result"]["files"]}
    stl_bytes_2 = second_files["body_stl"].read_bytes()
    report_text_2 = second_files["report_markdown"].read_text()
    step_size_2 = second_files["assembly_step"].stat().st_size

    assert stl_bytes_1 == stl_bytes_2
    assert report_text_1 == report_text_2
    assert step_size_1 == step_size_2
    assert step_size_2 > 0
