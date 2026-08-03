"""Safe output-path handling and atomic text writes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def resolve_report_path(output_directory: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute() or not relative_path.parts:
        raise ValueError(f"invalid report path: {relative_path}")
    root = output_directory.resolve()
    target = (root / relative_path).resolve()
    if target == root or root not in target.parents:
        raise ValueError(f"report path escapes output directory: {relative_path}")
    return target


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
