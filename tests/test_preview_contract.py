from zerorodcad.preview_data import PreviewMesh, PreviewScene
from zerorodcad_desktop.workers import PreviewSignals


def test_preview_scene_data_does_not_require_cadquery():
    mesh = PreviewMesh(
        name="body",
        vertices=((0.0, 0.0, 0.0),),
        triangles=(),
    )
    scene = PreviewScene(meshes=(mesh,))
    assert scene.meshes[0].name == "body"


def test_preview_worker_signal_contract():
    signals = PreviewSignals()
    assert hasattr(signals, "completed")
    assert hasattr(signals, "failed")
