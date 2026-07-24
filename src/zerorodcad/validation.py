"""Central validation service used by CLI and desktop UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose

from .parameters import ZeroRodParameters


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    values: dict[str, float | int | str] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_parameters(p: ZeroRodParameters, check_geometry: bool = False) -> ValidationResult:
    result = ValidationResult()

    if p.body_width <= 0 or p.body_depth <= 0 or p.fretboard_height <= 0:
        result.errors.append("Body dimensions must be positive.")
    if not isclose(p.fretboard_height, 6.90, abs_tol=1e-9):
        result.warnings.append("Fretboard height differs from the validated 6.90 mm reference.")
    if p.rod_diameter <= 0:
        result.errors.append("Rod diameter must be positive.")
    if p.groove_diameter <= 0:
        result.errors.append("Groove diameter must be positive.")
    if p.groove_diameter >= p.rod_diameter:
        result.errors.append("Groove diameter must be smaller than rod diameter.")
    if p.string_count < 1:
        result.errors.append("At least one string is required.")
    if any(gauge <= 0 for gauge in p.string_gauges_inch):
        result.errors.append("All string gauges must be positive.")
    if p.string_count > 1:
        required_width = p.string_spacing * (p.string_count - 1)
        if required_width + 2 * p.minimum_wall > p.body_width:
            result.errors.append("String spacing exceeds the usable body width.")
    if p.channel_diameter <= 0:
        result.errors.append("Channel diameter must be positive.")

    try:
        tangent_y, tangent_z = p.tangent_point_yz
    except ValueError as exc:
        result.errors.append(str(exc))
        tangent_y = tangent_z = float("nan")

    result.values.update(
        {
            "string_count": p.string_count,
            "rod_center_y_mm": p.rod_center_y,
            "rod_center_z_mm": p.rod_center_z,
            "rod_top_z_mm": p.rod_top_z,
            "tangent_y_mm": tangent_y,
            "tangent_z_mm": tangent_z,
            "entry_angle_deg": p.string_entry_angle_deg if not result.errors else float("nan"),
        }
    )

    if not result.errors and p.string_entry_angle_deg > 45:
        result.warnings.append(
            f"String entry angle is steep ({p.string_entry_angle_deg:.1f}°). "
            "Consider increasing body depth."
        )

    if check_geometry and not result.errors:
        try:
            from .model import build_body

            solids = build_body(p).solids().vals()
            if len(solids) != 1:
                result.errors.append(f"Body contains {len(solids)} solids instead of one.")
            elif not solids[0].isValid():
                result.errors.append("CadQuery reports an invalid body solid.")
        except Exception as exc:
            result.errors.append(f"Geometry validation failed: {exc}")

    return result
