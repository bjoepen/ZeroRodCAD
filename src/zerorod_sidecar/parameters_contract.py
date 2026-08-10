"""zerorod-parameters/v1 — parses a sidecar request's `parameters` object
into a zerorodcad.parameters.ZeroRodParameters instance.

Only structural (Level 1) and per-field-type (Level 2) checks live here.
zerorodcad.validation.validate_parameters remains the sole cross-parameter/
domain validator (Level 3) — this module never duplicates its rules, per
Build 023 M1's single-source-of-truth mandate (docs/contracts/
ZEROROD-PARAMETERS-V1.md).
"""

from __future__ import annotations

from typing import Any

from zerorod_sidecar.protocol import SidecarError
from zerorodcad.parameters import ZeroRodParameters, default_parameters

PARAMETERS_SCHEMA = "zerorod-parameters/v1"

# Every ZeroRodParameters field except project_name (str) and
# string_gauges_inch (array), which are checked separately below.
_NUMERIC_FIELDS = (
    "body_width",
    "body_depth",
    "fretboard_height",
    "rod_diameter",
    "groove_diameter",
    "rod_center_z_offset",
    "groove_front_clearance",
    "string_spacing",
    "string_inlet_y",
    "string_inlet_z",
    "channel_diameter",
    "channel_overrun_at_inlet",
    "channel_rod_clearance",
    "minimum_wall",
)


def _is_number(value: Any) -> bool:
    # bool is a subclass of int in Python; a JSON `true`/`false` must not
    # silently pass as a numeric field value.
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_field_types(values: dict[str, Any]) -> None:
    if "project_name" in values and not isinstance(values["project_name"], str):
        raise SidecarError(
            "invalid_parameter_type",
            "project_name must be a string",
            details={
                "field": "project_name",
                "expected": "string",
                "actual": type(values["project_name"]).__name__,
            },
        )

    for field_name in _NUMERIC_FIELDS:
        if field_name in values and not _is_number(values[field_name]):
            raise SidecarError(
                "invalid_parameter_type",
                f"{field_name} must be a number, got {type(values[field_name]).__name__}",
                details={
                    "field": field_name,
                    "expected": "number",
                    "actual": type(values[field_name]).__name__,
                },
            )

    if "string_gauges_inch" in values:
        gauges = values["string_gauges_inch"]
        if not isinstance(gauges, list) or not all(_is_number(g) for g in gauges):
            raise SidecarError(
                "invalid_parameter_type",
                "string_gauges_inch must be an array of numbers",
                details={
                    "field": "string_gauges_inch",
                    "expected": "array of numbers",
                    "actual": type(gauges).__name__,
                },
            )


def parse_parameters_request(parameters: dict[str, Any]) -> ZeroRodParameters:
    """Parses a sidecar request's `parameters` object into a
    ZeroRodParameters instance.

    An empty `parameters` object (`{}`, the Build 022 M2-M4 parameterless
    preview shape) returns the canonical defaults unchanged — this is the
    backward-compatibility path Build 023 M1 must preserve.
    """
    if not parameters:
        return default_parameters()

    schema = parameters.get("schema")
    if schema != PARAMETERS_SCHEMA:
        raise SidecarError(
            "invalid_parameters_schema",
            f"expected parameters.schema '{PARAMETERS_SCHEMA}', got {schema!r}",
            details={"expected": PARAMETERS_SCHEMA, "actual": schema},
        )

    values = parameters.get("values")
    if not isinstance(values, dict):
        raise SidecarError(
            "invalid_parameters",
            "parameters.values must be a JSON object",
            details={"expected": "object", "actual": type(values).__name__},
        )

    _check_field_types(values)

    try:
        return ZeroRodParameters.from_dict(values)
    except ValueError as exc:
        raise SidecarError("invalid_parameters", str(exc)) from exc


def parameters_to_contract(params: ZeroRodParameters) -> dict[str, Any]:
    """Wraps a ZeroRodParameters instance in the zerorod-parameters/v1
    envelope — used by the `parameters_defaults` command so a future
    frontend can consume the single authoritative default set instead of a
    hardcoded second copy."""
    return {"schema": PARAMETERS_SCHEMA, "values": params.to_dict()}
