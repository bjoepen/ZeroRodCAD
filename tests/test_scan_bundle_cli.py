from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from zerorod_analysis.build_metadata import BUILD_ID


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
    assert BUILD_ID in result.stdout


def test_dead_library_option_writes_all_reports(tmp_path: Path) -> None:
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
            "--dead-libraries",
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    deadlibs_dir = output_dir / "dead-libraries"
    assert (deadlibs_dir / "dead-libraries.json").is_file()
    assert (deadlibs_dir / "dead-libraries.md").is_file()
    assert (deadlibs_dir / "bundle-size-analysis.md").is_file()
    assert (deadlibs_dir / "optimization-report.md").is_file()
    assert (deadlibs_dir / "optimization-plan.md").is_file()
    assert not (output_dir / "macho").exists()


def test_dead_library_and_macho_options_can_be_combined(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            "tools/scan_bundle.py",
            str(make_bundle(tmp_path)),
            "--output-dir",
            str(output_dir),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--dead-libraries",
            "--macho-dependencies",
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "dead-libraries" / "dead-libraries.json").is_file()
    assert (output_dir / "macho").is_dir()
