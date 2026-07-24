from zerorodcad.parameters import ZeroRodParameters
from zerorodcad.validation import validate_parameters


def test_default_parameters_are_valid():
    result = validate_parameters(ZeroRodParameters())
    assert result.is_valid


def test_groove_larger_than_rod_is_rejected():
    p = ZeroRodParameters(groove_diameter=3.1)
    result = validate_parameters(p)
    assert not result.is_valid


def test_excessive_string_width_is_rejected():
    p = ZeroRodParameters(
        body_width=20.0,
        string_spacing=10.0,
        string_gauges_inch=(0.040, 0.030, 0.020, 0.012),
    )
    result = validate_parameters(p)
    assert not result.is_valid
