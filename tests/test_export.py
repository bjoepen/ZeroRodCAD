from pathlib import Path

from zerorodcad.export import expected_output_filenames, export_project
from zerorodcad.parameters import ZeroRodParameters


def test_export_accepts_valid_parameters(tmp_path: Path) -> None:
    exported_files = export_project(
        tmp_path,
        ZeroRodParameters(),
    )

    assert len(exported_files) == 3
    assert all(path.exists() for path in exported_files)


def test_expected_output_filenames_matches_real_export_output(tmp_path: Path) -> None:
    parameters = ZeroRodParameters(project_name="CBG Open G")
    expected = expected_output_filenames(parameters.project_name)

    body_path, assembly_path, report_path = export_project(tmp_path, parameters)

    assert expected == {
        "body_stl": body_path.name,
        "assembly_step": assembly_path.name,
        "report_markdown": report_path.name,
    }


def test_expected_output_filenames_empty_project_name_falls_back_to_zerorod() -> None:
    assert expected_output_filenames("") == {
        "body_stl": "zerorod-body.stl",
        "assembly_step": "zerorod-assembly.step",
        "report_markdown": "zerorod-report.md",
    }


def test_export_rejects_invalid_parameters(tmp_path: Path) -> None:
    parameters = ZeroRodParameters(body_width=0)

    try:
        export_project(tmp_path, parameters)
    except ValueError as exc:
        assert "Project validation failed" in str(exc)
    else:
        raise AssertionError("Invalid parameters were accepted.")
