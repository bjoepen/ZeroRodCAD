"""Create a Markdown instrument report."""

from __future__ import annotations

from pathlib import Path

from .parameters import ZeroRodParameters
from .validation import validate_parameters


def build_report(p: ZeroRodParameters) -> str:
    validation = validate_parameters(p)
    lines = [
        f"# Instrument Report – {p.project_name}",
        "",
        "## Parameters",
        "",
        "| Parameter | Value |",
        "|---|---:|",
        f"| Body width | {p.body_width:.2f} mm |",
        f"| Body depth | {p.body_depth:.2f} mm |",
        f"| Fretboard height | {p.fretboard_height:.2f} mm |",
        f"| Rod diameter | {p.rod_diameter:.2f} mm |",
        f"| Groove diameter | {p.groove_diameter:.2f} mm |",
        f"| Strings | {p.string_count} |",
        f"| String spacing | {p.string_spacing:.2f} mm |",
        f"| Entry angle | {p.string_entry_angle_deg:.2f}° |",
        "",
        "## Strings",
        "",
        "| No. | Gauge | Diameter | Height over fretboard |",
        "|---:|---:|---:|---:|",
    ]
    for index, (gauge, diameter, height) in enumerate(
        zip(
            p.string_gauges_inch,
            p.string_diameters_mm,
            p.string_heights_over_fretboard,
        ),
        start=1,
    ):
        lines.append(
            f"| {index} | {gauge:.3f} in | {diameter:.3f} mm | {height:.3f} mm |"
        )

    lines.extend(["", "## Validation", ""])
    if validation.errors:
        lines.extend(f"- ERROR: {message}" for message in validation.errors)
    if validation.warnings:
        lines.extend(f"- WARNING: {message}" for message in validation.warnings)
    if not validation.errors and not validation.warnings:
        lines.append("- All parameter checks passed.")

    lines.extend(
        [
            "",
            "## Notice",
            "",
            "The calculated geometry must be verified by CAD inspection, slicer review "
            "and a physical prototype before use.",
            "",
        ]
    )
    return "\n".join(lines)


def save_report(path: str | Path, p: ZeroRodParameters) -> Path:
    target = Path(path)
    target.write_text(build_report(p), encoding="utf-8")
    return target
