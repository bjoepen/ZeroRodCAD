from pathlib import Path

from zerorodcad.export import export_project
from zerorodcad.parameters import ZeroRodParameters


def test_export_accepts_valid_parameters(tmp_path: Path) -> None:
    exported_files = export_project(
        tmp_path,
        ZeroRodParameters(),
    )

    assert len(exported_files) == 3
    assert all(path.exists() for path in exported_files)


def test_export_rejects_invalid_parameters(tmp_path: Path) -> None:
    parameters = ZeroRodParameters(body_width=0)

    try:
        export_project(tmp_path, parameters)
    except ValueError as exc:
        assert "Project validation failed" in str(exc)
    else:
        raise AssertionError("Invalid parameters were accepted.")
