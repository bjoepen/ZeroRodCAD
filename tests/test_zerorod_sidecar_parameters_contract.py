"""Tests for zerorod_sidecar.parameters_contract (Build 023 M1)."""

from __future__ import annotations

import pytest

from zerorod_sidecar.parameters_contract import (
    PARAMETERS_SCHEMA,
    parameters_to_contract,
    parse_parameters_request,
)
from zerorod_sidecar.protocol import SidecarError
from zerorodcad.parameters import ZeroRodParameters, default_parameters


def test_empty_parameters_returns_canonical_defaults():
    assert parse_parameters_request({}) == default_parameters()


def test_full_explicit_default_values_round_trips_to_defaults():
    contract = parameters_to_contract(default_parameters())
    assert contract["schema"] == PARAMETERS_SCHEMA
    parsed = parse_parameters_request({"schema": PARAMETERS_SCHEMA, "values": contract["values"]})
    assert parsed == default_parameters()


def test_partial_values_fall_back_to_dataclass_defaults_for_omitted_fields():
    parsed = parse_parameters_request({"schema": PARAMETERS_SCHEMA, "values": {"body_width": 50.0}})
    assert parsed.body_width == 50.0
    assert parsed.body_depth == default_parameters().body_depth


def test_wrong_schema_raises_invalid_parameters_schema():
    with pytest.raises(SidecarError) as excinfo:
        parse_parameters_request({"schema": "not-a-real-schema", "values": {}})
    assert excinfo.value.code == "invalid_parameters_schema"


def test_missing_schema_on_nonempty_parameters_raises():
    with pytest.raises(SidecarError) as excinfo:
        parse_parameters_request({"values": {"body_width": 50.0}})
    assert excinfo.value.code == "invalid_parameters_schema"


def test_non_object_values_raises_invalid_parameters():
    with pytest.raises(SidecarError) as excinfo:
        parse_parameters_request({"schema": PARAMETERS_SCHEMA, "values": "nope"})
    assert excinfo.value.code == "invalid_parameters"


def test_unknown_field_name_raises_invalid_parameters():
    with pytest.raises(SidecarError) as excinfo:
        parse_parameters_request(
            {"schema": PARAMETERS_SCHEMA, "values": {"totally_made_up_field": 1.0}}
        )
    assert excinfo.value.code == "invalid_parameters"


@pytest.mark.parametrize(
    "field_name,bad_value",
    [
        ("body_width", "wide"),
        ("body_depth", None),
        ("fretboard_height", [1, 2]),
        ("rod_diameter", True),
        ("channel_rod_clearance", {"nested": 1}),
    ],
)
def test_wrong_type_for_numeric_field_raises_invalid_parameter_type(field_name, bad_value):
    with pytest.raises(SidecarError) as excinfo:
        parse_parameters_request({"schema": PARAMETERS_SCHEMA, "values": {field_name: bad_value}})
    assert excinfo.value.code == "invalid_parameter_type"
    assert excinfo.value.details["field"] == field_name


def test_wrong_type_for_project_name_raises_invalid_parameter_type():
    with pytest.raises(SidecarError) as excinfo:
        parse_parameters_request({"schema": PARAMETERS_SCHEMA, "values": {"project_name": 123}})
    assert excinfo.value.code == "invalid_parameter_type"
    assert excinfo.value.details["field"] == "project_name"


def test_wrong_type_for_string_gauges_raises_invalid_parameter_type():
    with pytest.raises(SidecarError) as excinfo:
        parse_parameters_request(
            {"schema": PARAMETERS_SCHEMA, "values": {"string_gauges_inch": "0.036,0.026"}}
        )
    assert excinfo.value.code == "invalid_parameter_type"
    assert excinfo.value.details["field"] == "string_gauges_inch"


def test_string_gauges_with_non_numeric_entry_raises_invalid_parameter_type():
    with pytest.raises(SidecarError) as excinfo:
        parse_parameters_request(
            {"schema": PARAMETERS_SCHEMA, "values": {"string_gauges_inch": [0.036, "bad"]}}
        )
    assert excinfo.value.code == "invalid_parameter_type"


def test_valid_string_gauges_list_of_numbers_parses():
    parsed = parse_parameters_request(
        {"schema": PARAMETERS_SCHEMA, "values": {"string_gauges_inch": [0.040, 0.030, 1]}}
    )
    assert parsed.string_gauges_inch == (0.040, 0.030, 1.0)


def test_parameters_to_contract_round_trips_a_non_default_instance():
    params = ZeroRodParameters(project_name="Test", body_depth=10.0)
    contract = parameters_to_contract(params)
    parsed = parse_parameters_request(contract)
    assert parsed == params
