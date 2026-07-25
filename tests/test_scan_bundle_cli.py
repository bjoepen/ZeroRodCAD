from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def make_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "CLI.app"
    executable_dir = bundle / "Contents" / "MacOS"
    executable_dir.mkdir(parents=True)
    (executable_dir / "CLI").write_bytes(b"#!/bin/sh\n")
    return bundle


def test_direct_script_execution_from_repository_root(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "reports"
    cache_dir = tmp_path / "cache"
    result = subprocess.run(
        [
            sys.executable,
            "tools/scan_bundle.py",
            str(make_bundle(tmp_path)),
            "--output-dir",
            str(output_dir),
            "--cache-dir",
            str(cache_dir),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "scanner2" / "scanner2-report.md").is_file()
    assert (output_dir / "scanner2" / "scanner2-inventory.json").is_file()


def test_module_execution_reports_version() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tools.scan_bundle", "--version"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "019.2" in result.stdout
