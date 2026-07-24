from zerorodcad_desktop.app import parse_arguments
from zerorodcad_desktop.application_info import APP_BUILD, APP_VERSION
from zerorodcad_desktop.startup import log_directory


def test_build_metadata():
    assert APP_BUILD == "015"
    assert APP_VERSION == "0.15.0"


def test_startup_test_argument():
    arguments = parse_arguments(["--startup-test"])
    assert arguments.startup_test is True


def test_log_directory_is_absolute():
    assert log_directory().is_absolute()
