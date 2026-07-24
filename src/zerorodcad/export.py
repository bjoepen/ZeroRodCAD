"""Export service for STL, STEP and the engineering report."""

from __future__ import annotations

from pathlib import Path

from .parameters import ZeroRodParameters
from .report import save_report
from .validation import validate_parameters


def export_project(
    output_directory: str | Path,
    parameters: ZeroRodParameters,
) -> tuple[Path, ...]:
    validation = validate_parameters(parameters)
    if not validation.ok:
        messages = "\n".join(validation.errors)
        raise ValueError(f"Project validation failed:\n{messages}")

    # Deliberately lazy: importing CadQuery/OCP during application startup made
    # packaged builds fragile and delayed the first window.
    from cadquery import exporters

    from .model import build_assembly, build_body

    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_name(parameters.project_name)
    body_path = directory / f"{safe_name}-body.stl"
    assembly_path = directory / f"{safe_name}-assembly.step"
    report_path = directory / f"{safe_name}-report.md"

    exporters.export(build_body(parameters), str(body_path))
    exporters.export(build_assembly(parameters), str(assembly_path))
    save_report(report_path, parameters)

    return body_path, assembly_path, report_path


def _safe_name(value: str) -> str:
    cleaned = "".join(
        character.lower() if character.isalnum() else "-" for character in value.strip()
    )
    return "-".join(part for part in cleaned.split("-") if part) or "zerorod"
