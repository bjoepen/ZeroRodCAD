from zerorodcad_desktop.application_info import APP_BUILD, APP_NAME, APP_VERSION
from zerorodcad_desktop.diagnostics import collect_diagnostics, diagnostics_as_text


def test_application_metadata():
    assert APP_NAME == "ZeroRodCAD Desktop"
    assert APP_VERSION == "0.12.0"
    assert APP_BUILD == "012"


def test_diagnostics_have_core_items():
    names = {item.name for item in collect_diagnostics()}
    assert {"Platform", "Machine", "Python", "Executable", "CadQuery", "PySide6"} <= names


def test_diagnostics_text_has_title():
    assert diagnostics_as_text().startswith("ZeroRodCAD Desktop Diagnostics")
