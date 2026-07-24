"""Read and write human-readable .zerorod project files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .parameters import ZeroRodParameters

FILE_FORMAT = "ZeroRodCAD Project"
FILE_VERSION = 1


def save_project(path: str | Path, parameters: ZeroRodParameters) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".zerorod":
        target = target.with_suffix(".zerorod")
    payload: dict[str, Any] = {
        "format": FILE_FORMAT,
        "version": FILE_VERSION,
        "parameters": parameters.to_dict(),
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_project(path: str | Path) -> ZeroRodParameters:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("format") != FILE_FORMAT:
        raise ValueError("Not a ZeroRodCAD project file.")
    if payload.get("version") != FILE_VERSION:
        raise ValueError(f"Unsupported project version: {payload.get('version')}")
    return ZeroRodParameters.from_dict(payload["parameters"])
