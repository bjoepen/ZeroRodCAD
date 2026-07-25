from __future__ import annotations

import subprocess
from pathlib import Path


def otool_dependencies(path: Path) -> list[str]:
    process = subprocess.run(
        ["otool", "-L", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return []
    return [
        line.strip().split(" (compatibility", 1)[0]
        for line in process.stdout.splitlines()[1:]
        if line.strip()
    ]


def macho_id(path: Path) -> str | None:
    process = subprocess.run(
        ["otool", "-D", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return None
    lines = [line.strip() for line in process.stdout.splitlines()[1:] if line.strip()]
    return lines[0] if lines else None
