from zerorodcad.parameters import ZeroRodParameters
from zerorodcad.project import load_project, save_project


def test_save_and_load_project(tmp_path):
    original = ZeroRodParameters(project_name="Roundtrip", body_depth=10.0)
    path = save_project(tmp_path / "roundtrip", original)
    assert path.suffix == ".zerorod"
    assert load_project(path) == original
