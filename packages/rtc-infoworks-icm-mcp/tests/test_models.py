import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError
from rtc_infoworks_icm_mcp.models import (
    BoundInput,
    DefinitionInput,
    Diagnostic,
    EditRequest,
    Operation,
    RequestError,
    parse_definition,
    parse_edits,
)

from rtc_infoworks_icm import (
    ControllerType,
    LogicOperator,
    RangeType,
    RuleType,
    TableType,
    VariableOperator,
)

operation_adapter = TypeAdapter(Operation)
bound_adapter = TypeAdapter(BoundInput)


@pytest.mark.parametrize(
    ("enum", "operation"),
    [
        (RangeType, {"method": "range_", "name": "level"}),
        (
            TableType,
            {
                "method": "table",
                "name": "curve",
                "input_range": {"ref": "r"},
                "rows": [],
            },
        ),
        (
            LogicOperator,
            {"method": "logic", "name": "test", "condition_1": {"ref": "r"}},
        ),
        (
            ControllerType,
            {"method": "controller", "name": "pid", "measurement_interval": 60},
        ),
        (RuleType, {"method": "rule"}),
        (
            VariableOperator,
            {"method": "assign_variable", "target": {"ref": "v"}, "argument_1": 1},
        ),
    ],
)
def test_wire_enums_use_every_core_value(
    enum: type[
        RangeType
        | TableType
        | LogicOperator
        | ControllerType
        | RuleType
        | VariableOperator
    ],
    operation: dict[str, object],
) -> None:
    field = "operator" if enum in (LogicOperator, VariableOperator) else "type"
    for member in enum:
        payload = {"id": "op", **operation, field: member.value}
        parsed = operation_adapter.validate_json(json.dumps(payload))
        assert parsed.model_dump(mode="json")[field] == member.value
        payload[field] = member.name if member.name != member.value else "UNKNOWN"
        with pytest.raises(ValidationError):
            operation_adapter.validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "operation",
    [
        {"method": "eval", "id": "x", "source": "print(1)"},
        {"method": "comment", "id": "x", "text": 1},
        {"method": "comment", "id": "x", "text": "ok", "extra": 1},
        {"method": "comment", "id": "bad id", "text": "ok"},
        {"method": "rule", "id": "x", "type": "POS", "fixed_value": True},
        {"method": "rule", "id": "x", "type": "POS", "fixed_value": "1"},
        {"method": "rule", "id": "x", "type": "POS", "fixed_value": float("inf")},
        {"method": "rule", "id": "x", "type": "POS", "fixed_value": float("nan")},
        {"method": "rule", "id": "x", "type": "POS", "variable_value": "value"},
        {
            "method": "rule",
            "id": "x",
            "type": "POS",
            "variable_value": {"ref": "v", "x": 1},
        },
        {
            "method": "controller",
            "id": "x",
            "name": "pid",
            "type": "PID",
            "measurement_interval": 1.0,
        },
        {
            "method": "regulator",
            "id": "x",
            "regulator_id": "W1",
            "override_other_control": 1,
        },
        {
            "method": "assign_variable",
            "id": "x",
            "target": {"ref": "v"},
            "operator": "=",
        },
        {
            "method": "table",
            "id": "x",
            "name": "t",
            "type": "STEP",
            "input_range": {"ref": "r"},
            "rows": [[1, 2]],
        },
    ],
)
def test_operations_reject_ambiguous_or_coerced_inputs(
    operation: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        operation_adapter.validate_json(json.dumps(operation))


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "number", "value": False},
        {"kind": "number", "value": "1"},
        {"kind": "number", "value": float("-inf")},
        {"kind": "datetime", "value": "2026-02-30T12:00:00"},
        {"kind": "datetime", "value": "2026-01-01T00:00:00Z"},
        {"kind": "datetime", "value": "2026-01-01T00:00:00+01:00"},
        {"kind": "datetime", "value": "2026-01-01 00:00:00"},
        {"kind": "datetime", "value": "2026-01-01T00:00:00.001"},
        {"kind": "datetime", "value": "0001-01-01T00:00:00"},
        {"kind": "time", "value": "24:00:00"},
        {"kind": "time", "value": "01:00:00Z"},
        {"kind": "time", "value": "01:00:00.5"},
        {"kind": "weekly_time", "value": "01:00:00", "weekday": True},
        {"kind": "weekly_time", "value": "01:00:00", "weekday": 0},
        {"kind": "weekly_time", "value": "01:00:00", "weekday": 8},
        {"kind": "weekly_time", "value": "01:00:00", "weekday": "1"},
        {"kind": "duration", "value": 1},
    ],
)
def test_bound_inputs_reject_lossy_or_invalid_values(value: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        bound_adapter.validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "number", "value": 1},
        {"kind": "number", "value": 0.5},
        {"kind": "datetime", "value": "2026-01-01T12:00:00"},
        {"kind": "time", "value": "12:00:00"},
        {"kind": "weekly_time", "value": "12:00:00", "weekday": 7},
    ],
)
def test_bounds_round_trip(value: dict[str, object]) -> None:
    assert (
        bound_adapter.validate_json(json.dumps(value)).model_dump(mode="json") == value
    )


def test_definition_round_trip_is_immutable_and_preserves_order() -> None:
    payload = {
        "name": "Control",
        "operations": [
            {"method": "declare_variable", "id": "v", "name": "total"},
            {
                "method": "assign_variable",
                "id": "a",
                "target": {"ref": "v"},
                "operator": "+",
                "argument_1": {"ref": "v"},
                "argument_2": 1,
            },
        ],
    }
    definition = DefinitionInput.model_validate_json(json.dumps(payload))
    assert isinstance(definition.operations, tuple)
    assert [operation.id for operation in definition.operations] == ["v", "a"]
    assert (
        DefinitionInput.model_validate_json(definition.model_dump_json()) == definition
    )
    with pytest.raises(ValidationError, match="frozen"):
        definition.name = "Changed"


def test_edit_contracts_use_explicit_targets_and_positions() -> None:
    request = EditRequest.model_validate_json(
        json.dumps(
            {
                "definition_id": "control",
                "expected_revision": 0,
                "edits": [
                    {
                        "action": "insert",
                        "before": "rule",
                        "operation": {
                            "id": "note",
                            "method": "comment",
                            "text": "Review",
                        },
                    },
                    {
                        "action": "replace",
                        "target": "note",
                        "operation": {
                            "id": "note",
                            "method": "comment",
                            "text": "Updated",
                        },
                    },
                    {"action": "remove", "target": "note"},
                ],
            }
        )
    )
    assert [edit.action for edit in request.edits] == ["insert", "replace", "remove"]
    for revision in (-1, True, "1"):
        with pytest.raises(ValidationError):
            EditRequest.model_validate_json(
                json.dumps(
                    {
                        "definition_id": "control",
                        "expected_revision": revision,
                        "edits": [],
                    }
                )
            )


def test_contract_schemas_match_reviewed_snapshot() -> None:
    expected = json.loads(Path(__file__).with_name("contracts.schema.json").read_text())
    actual = {
        "definition": DefinitionInput.model_json_schema(),
        "edits": EditRequest.model_json_schema(),
        "diagnostic": Diagnostic.model_json_schema(),
    }
    assert actual == expected


def test_malformed_requests_return_context_without_input_values() -> None:
    with pytest.raises(RequestError) as caught:
        parse_definition(
            json.dumps(
                {
                    "name": "Control",
                    "operations": [
                        {
                            "id": "x",
                            "method": "rule",
                            "type": "POS",
                            "fixed_value": "secret",
                        },
                    ],
                }
            )
        )
    for diagnostic in caught.value.diagnostics:
        assert diagnostic.code == "invalid_request"
        assert diagnostic.operation_index == 0
        assert diagnostic.field is not None and "fixed_value" in diagnostic.field
        assert "secret" not in diagnostic.model_dump_json()
    with pytest.raises(RequestError):
        parse_definition("{")
    with pytest.raises(RequestError):
        parse_edits('{"definition_id":"x","expected_revision":0,"edits":[]}')


def test_sdk_decoded_arrays_and_json_decode_have_identical_contracts() -> None:
    payload = {
        "name": "Control",
        "operations": [
            {
                "id": "r",
                "method": "range_",
                "name": "level",
                "type": "Z",
                "location": "N1",
            },
            {
                "id": "t",
                "method": "table",
                "name": "curve",
                "type": "STEP",
                "input_range": {"ref": "r"},
                "rows": [{"input": {"kind": "number", "value": 0}, "output": 1}],
            },
        ],
    }
    assert DefinitionInput.model_validate(payload) == parse_definition(
        json.dumps(payload)
    )
