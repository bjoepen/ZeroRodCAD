"""Validated geometry export."""

from __future__ import annotations

from pathlib import Path

from cadquery import exporters

from .model import build_assembly, build_body
from .parameters import ZeroRodParameters
from .report import save_report
from .validation import validate_parameters


def export_project(
    output_directory: str | Path,
    parameters: ZeroRodParameters,
    *,
    export_stl: bool = True,
    export_step: bool = True,
    export_report: bool = True,
) -> list[Path]:
    validation = validate_parameters(parameters, check_geometry=True)
    if not validation.is_valid:
        raise ValueError("Export blocked: " + " | ".join(validation.errors))

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    slug = _slugify(parameters.project_name)
    created: list[Path] = []

    body = build_body(parameters)

    if export_stl:
        path = output / f"{slug}.stl"
        exporters.export(body, str(path))
        created.append(path)

    if export_step:
        path = output / f"{slug}.step"
        build_assembly(parameters).save(str(path))
        created.append(path)

    if export_report:
        path = output / f"{slug}-instrument-report.md"
        save_report(path, parameters)
        created.append(path)

    return created


def _slugify(value: str) -> str:
    safe = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.split("-") if part) or "zerorod"
