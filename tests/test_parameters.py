from math import isclose

from zerorodcad.parameters import ZeroRodParameters


def test_default_string_positions_are_centered():
    p = ZeroRodParameters()
    assert p.string_positions_x == (-10.0, 0.0, 10.0)


def test_four_strings_are_centered():
    p = ZeroRodParameters(
        string_gauges_inch=(0.040, 0.030, 0.020, 0.012),
        string_spacing=8.0,
    )
    assert p.string_positions_x == (-12.0, -4.0, 4.0, 12.0)


def test_tangent_is_perpendicular():
    p = ZeroRodParameters()
    radius_y = p.channel_contact_y - p.rod_center_y
    radius_z = p.channel_contact_z - p.rod_center_z
    channel_y = p.channel_contact_y - p.string_inlet_y
    channel_z = p.channel_contact_z - p.string_inlet_z
    assert isclose(radius_y * channel_y + radius_z * channel_z, 0.0, abs_tol=1e-9)


def test_project_roundtrip_dictionary():
    original = ZeroRodParameters(project_name="Test", body_depth=10.0)
    restored = ZeroRodParameters.from_dict(original.to_dict())
    assert restored == original
