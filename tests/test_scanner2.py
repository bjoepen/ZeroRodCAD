from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools.bundle_analyzer.scanner2 import (
    BundleSection,
    ScanFilter,
    Scanner,
    normalize_extensions,
)


def make_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "Example.app"
    contents = bundle / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Frameworks" / "vtkmodules").mkdir(parents=True)
    (contents / "Resources" / "OCP").mkdir(parents=True)
    (contents / "Resources" / "module.py").write_text("value = 1\n")
    (contents / "Frameworks" / "libsame.dylib").write_bytes(b"same")
    (contents / "Frameworks" / "vtkmodules" / "libsame.dylib").write_bytes(b"same")
    (contents / "Resources" / "OCP" / "data.bin").write_bytes(b"ocp")
    (contents / "MacOS" / "Example").write_bytes(b"#!/bin/sh\n")
    return bundle


def test_scanner_builds_indexes_and_statistics(tmp_path: Path) -> None:
    database = Scanner().scan(make_bundle(tmp_path), cache_dir=tmp_path / "cache")

    assert database.statistics.file_count == 5
    assert len(database.hash_index) == 4
    assert (
        len(
            database.hash_index[
                next(iter(key for key, values in database.hash_index.items() if len(values) == 2))
            ]
        )
        == 2
    )
    assert database.section_index[BundleSection.VTK]
    assert database.section_index[BundleSection.OCP]
    assert database.statistics.python_count == 1


def test_second_scan_uses_cache(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    scanner = Scanner()
    cache_dir = tmp_path / "cache"

    first = scanner.scan(bundle, cache_dir=cache_dir)
    second = scanner.scan(bundle, cache_dir=cache_dir)

    assert first.statistics.cache_misses == 5
    assert second.statistics.cache_hits == 5
    assert second.statistics.cache_misses == 0


def test_filter_by_extension_and_section(tmp_path: Path) -> None:
    scan_filter = ScanFilter(
        include_sections=frozenset({BundleSection.FRAMEWORKS}),
        extensions=normalize_extensions(["dylib"]),
    )
    database = Scanner().scan(
        make_bundle(tmp_path),
        cache_dir=tmp_path / "cache",
        scan_filter=scan_filter,
    )

    assert len(database.files) == 1
    assert database.files[0].relative_path.endswith("libsame.dylib")


def test_invalid_bundle_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Scanner().scan(tmp_path / "missing.app")


def test_cache_is_valid_json(tmp_path: Path) -> None:
    Scanner().scan(make_bundle(tmp_path), cache_dir=tmp_path / "cache")
    payload = json.loads((tmp_path / "cache" / "scanner2-cache.json").read_text())
    assert payload["version"] == 2
    assert len(payload["entries"]) == 5
