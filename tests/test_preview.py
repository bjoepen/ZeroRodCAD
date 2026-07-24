import pytest

pytest.importorskip("cadquery")

from zerorodcad.parameters import ZeroRodParameters
from zerorodcad.preview import build_preview_scene, build_virtual_strings


def test_preview_scene_contains_body_and_rod():
    scene = build_preview_scene(ZeroRodParameters())
    assert {mesh.name for mesh in scene.meshes} == {"body", "rod"}
    assert all(mesh.vertices for mesh in scene.meshes)
    assert all(mesh.triangles for mesh in scene.meshes)


def test_virtual_strings_follow_string_count():
    p = ZeroRodParameters(
        string_gauges_inch=(0.040, 0.030, 0.020, 0.012),
        string_spacing=8.0,
    )
    lines = build_virtual_strings(p)
    assert len(lines) == 8


def test_each_virtual_string_reaches_tangent_point():
    p = ZeroRodParameters()
    lines = build_virtual_strings(p)
    for index in range(p.string_count):
        first_segment = lines[index * 2]
        second_segment = lines[index * 2 + 1]
        assert first_segment[1] == second_segment[0]
        assert first_segment[1][1:] == p.tangent_point_yz
