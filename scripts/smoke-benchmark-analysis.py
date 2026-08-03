"""Temporary, non-destructive smoke test for the Build 020 M4 benchmark CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="zerorod-benchmark-smoke-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        executable = temporary_root / "Smoke.app" / "Contents" / "MacOS" / "smoke"
        executable.parent.mkdir(parents=True)
        executable.write_text("not Mach-O", encoding="utf-8")
        output = temporary_root / "benchmark.json"
        subprocess.run(
            [
                sys.executable,
                "tools/benchmark_analysis.py",
                str(executable.parents[2]),
                "--warmup",
                "1",
                "--iterations",
                "2",
                "--no-cache",
                "--json-output",
                str(output),
            ],
            cwd=repository_root,
            check=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload["iterations"] != 2 or payload["warmup"] != 1:
            raise RuntimeError("benchmark smoke test returned invalid iteration metadata")


if __name__ == "__main__":
    main()
