import pytest

pytest.importorskip("cadquery")

from zerorodcad.model import build_body, build_channel_cutters, build_rod
from zerorodcad.parameters import ZeroRodParameters


@pytest.mark.parametrize("depth", [8.0, 9.0, 10.0])
def test_body_is_one_valid_solid(depth):
    body = build_body(ZeroRodParameters(body_depth=depth))
    solids = body.solids().vals()
    assert len(solids) == 1
    assert solids[0].isValid()


@pytest.mark.parametrize("count", [1, 3, 4, 6])
def test_variable_string_counts_create_valid_body(count):
    gauges = tuple(0.020 for _ in range(count))
    p = ZeroRodParameters(
        body_width=max(38.0, (count - 1) * 6.0 + 4.0),
        string_gauges_inch=gauges,
        string_spacing=6.0,
    )
    solids = build_body(p).solids().vals()
    assert len(solids) == 1
    assert solids[0].isValid()


def test_channels_do_not_intersect_rod():
    p = ZeroRodParameters()
    overlap = build_channel_cutters(p).intersect(build_rod(p))
    assert overlap.solids().size() == 0
