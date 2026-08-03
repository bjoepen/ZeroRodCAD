from __future__ import annotations

from pathlib import Path

import pytest

from zerorod_analysis.runtime.normalize import normalize_path
from zerorod_analysis.runtime.serialization import validate_output_path


def test_bundle_paths_are_relative_and_private_paths_redacted(tmp_path) -> None:
    bundle = tmp_path / "Demo.app"
    inside = bundle / "Contents" / "Frameworks" / "libDemo.dylib"
    normalized = normalize_path(inside, bundle_root=bundle, home=tmp_path / "home")
    assert normalized.bundle_relative_path == "Contents/Frameworks/libDemo.dylib"
    private = normalize_path(tmp_path / "home" / "secret.so", home=tmp_path / "home")
    assert "secret" not in private.identity and str(tmp_path) not in private.identity


def test_output_rejects_bundle_and_traversal(tmp_path) -> None:
    bundle = tmp_path / "Demo.app"
    with pytest.raises(ValueError, match="outside"):
        validate_output_path(bundle / "trace.json", bundle)
    with pytest.raises(ValueError, match="traversal"):
        validate_output_path(Path("reports/../trace.json"), bundle)
