import json
from datetime import datetime, time

import pytest
from rtc_infoworks_icm_mcp.builder import (
    BuildError,
    build_definition,
    validate_definition,
)
from rtc_infoworks_icm_mcp.models import DefinitionInput, Diagnostic

from rtc_infoworks_icm import (
    ControllerType,
    LogicOperator,
    RangeType,
    RTCCreator,
    RuleType,
    TableType,
    VariableOperator,
)


def definition(operations: list[dict[str, object]]) -> DefinitionInput:
    return DefinitionInput.model_validate_json(
        json.dumps({"name": "Control", "operations": operations})
    )


def closing_operations() -> list[dict[str, object]]:
    return [
        {"id": "reg", "method": "regulator", "regulator_id": "W1"},
        {"id": "rule", "method": "rule", "type": "POS"},
    ]


def test_all_operations_match_direct_library_calls() -> None:
    operations: list[dict[str, object]] = [
        {"id": "note", "method": "comment", "text": "Global"},
        {
            "id": "level",
            "method": "range_",
            "name": "level",
            "type": "Z",
            "location": "N1",
            "minimum": {"kind": "number", "value": 1},
            "maximum": {"kind": "number", "value": 2},
            "distance": 4,
        },
        {"id": "total", "method": "declare_variable", "name": "total"},
        {
            "id": "initial",
            "method": "assign_variable",
            "target": {"ref": "total"},
            "operator": "+",
            "argument_1": {"ref": "total"},
            "argument_2": 1,
            "measurement": "m",
        },
        {
            "id": "update",
            "method": "assign_variable",
            "target": {"ref": "total"},
            "operator": "*",
            "argument_1": {"ref": "total"},
            "argument_2": 2,
        },
        {
            "id": "varrange",
            "method": "range_",
            "name": "varrange",
            "type": "VAR",
            "location": {"ref": "total"},
        },
        {
            "id": "curve",
            "method": "table",
            "name": "curve",
            "type": "STEP",
            "input_range": {"ref": "level"},
            "rows": [{"input": {"kind": "number", "value": 1}, "output": 2}],
            "output_measurement": "FLOW",
        },
        {
            "id": "logic",
            "method": "logic",
            "name": "high",
            "operator": "NOT",
            "condition_1": {"ref": "level"},
        },
        {
            "id": "pid",
            "method": "controller",
            "name": "pid",
            "type": "PID",
            "measurement_interval": 60,
            "sensor": {"ref": "level"},
            "filter_coefficient": 0.5,
            "proportional": -1,
            "integral": 0.1,
            "differential": 0.05,
        },
        {
            "id": "reg",
            "method": "regulator",
            "regulator_id": "W1",
            "initial": -1,
            "threshold": 0.1,
            "positive_rate": 0.2,
            "negative_rate": 0.3,
            "override_other_control": True,
        },
        {
            "id": "rule",
            "method": "rule",
            "type": "CTRL",
            "condition": {"ref": "logic"},
            "controller": {"ref": "pid"},
            "fixed_value": 1,
            "variable_value": {"ref": "curve"},
        },
    ]
    spec = definition(operations)
    original = spec.model_dump_json()
    built = build_definition(spec)
    validate_definition(spec)
    direct = RTCCreator("Control")
    direct.comment("Global")
    level = direct.range_("level", RangeType.LEVEL, "N1", 1, 2, 4)
    total = direct.variable("total")
    direct.variable(total, VariableOperator.ADD, total, 1, measurement="m")
    direct.variable(total, VariableOperator.MULTIPLY, total, 2)
    direct.range_("varrange", RangeType.VARIABLE, total)
    curve = direct.table("curve", level, TableType.STEP, [(1, 2)], "FLOW")
    high = direct.logic("high", LogicOperator.NOT, level)
    pid = direct.controller("pid", ControllerType.PID, 60, level, 0.5, -1, 0.1, 0.05)
    direct.regulator("W1", -1, 0.1, 0.2, 0.3, True)
    direct.rule(RuleType.CONTROL, high, pid, 1, curve)
    assert built.render() == direct.render()
    assert spec.model_dump_json() == original
    assert build_definition(spec).render() == built.render()
    built.comment("Independent")
    assert build_definition(spec).render() == direct.render()


@pytest.mark.parametrize(
    ("range_type", "kind", "first", "second", "weekday"),
    [
        ("T", "datetime", "2026-01-01T00:00:00", "2026-01-02T00:00:00", None),
        ("LCT", "datetime", "2026-01-01T00:00:00", "2026-01-02T00:00:00", None),
        ("TR", "time", "06:00:00", "18:00:00", None),
        ("LCTR", "weekly_time", "06:00:00", "18:00:00", 1),
    ],
)
def test_temporal_conversion_matches_core(
    range_type: str, kind: str, first: str, second: str, weekday: int | None
) -> None:
    low: dict[str, object] = {"kind": kind, "value": first}
    high: dict[str, object] = {"kind": kind, "value": second}
    if weekday is not None:
        low["weekday"] = high["weekday"] = weekday
    spec = definition(
        [
            {
                "id": "clock",
                "method": "range_",
                "name": "clock",
                "type": range_type,
                "minimum": low,
                "maximum": high,
            },
            {
                "id": "curve",
                "method": "table",
                "name": "curve",
                "type": "LINEAR",
                "input_range": {"ref": "clock"},
                "rows": [{"input": low, "output": 0}, {"input": high, "output": 1}],
            },
            *closing_operations(),
        ]
    )
    direct = RTCCreator("Control")
    if kind == "datetime":
        minimum = datetime.fromisoformat(first)
        maximum = datetime.fromisoformat(second)
    elif weekday is not None:
        minimum = (weekday, time.fromisoformat(first))
        maximum = (weekday, time.fromisoformat(second))
    else:
        minimum = time.fromisoformat(first)
        maximum = time.fromisoformat(second)
    clock = direct.range_(
        "clock", RangeType(range_type), minimum=minimum, maximum=maximum
    )
    direct.table("curve", clock, TableType.LINEAR, [(minimum, 0), (maximum, 1)])
    direct.regulator("W1")
    direct.rule(RuleType.POSITION)
    assert build_definition(spec).render() == direct.render()


@pytest.mark.parametrize(
    ("operations", "code", "index", "field"),
    [
        (
            [
                {"id": "x", "method": "comment", "text": "A"},
                {"id": "x", "method": "comment", "text": "B"},
            ],
            "duplicate_operation_id",
            1,
            "id",
        ),
        (
            [
                {
                    "id": "r",
                    "method": "rule",
                    "type": "POS",
                    "variable_value": {"ref": "missing"},
                }
            ],
            "unknown_reference",
            0,
            "variable_value",
        ),
        (
            [
                {"id": "note", "method": "comment", "text": "Note"},
                {
                    "id": "r",
                    "method": "rule",
                    "type": "POS",
                    "variable_value": {"ref": "note"},
                },
            ],
            "unknown_reference",
            1,
            "variable_value",
        ),
        (
            [
                {
                    "id": "pid",
                    "method": "controller",
                    "name": "pid",
                    "type": "PID",
                    "measurement_interval": 60,
                },
                {
                    "id": "r",
                    "method": "rule",
                    "type": "POS",
                    "variable_value": {"ref": "pid"},
                },
            ],
            "wrong_reference_kind",
            1,
            "variable_value",
        ),
        (
            [
                {
                    "id": "x",
                    "method": "range_",
                    "name": "bad\nname",
                    "type": "Z",
                    "location": "N1",
                }
            ],
            "invalid_document",
            0,
            None,
        ),
        (
            [
                {"id": "v", "method": "declare_variable", "name": "v"},
                {
                    "id": "range",
                    "method": "range_",
                    "name": "range",
                    "type": "VAR",
                    "location": {"ref": "v"},
                },
            ],
            "invalid_document",
            1,
            None,
        ),
        ([{"id": "r", "method": "rule", "type": "POS"}], "invalid_document", 0, None),
    ],
)
def test_build_errors_have_stable_context(
    operations: list[dict[str, object]], code: str, index: int, field: str | None
) -> None:
    spec = definition(operations)
    before = spec.model_dump_json()
    with pytest.raises(BuildError) as caught:
        build_definition(spec)
    diagnostic = caught.value.diagnostic
    assert diagnostic.code == code
    assert diagnostic.operation_index == index
    assert diagnostic.operation_id == operations[index]["id"]
    assert diagnostic.field == field
    assert diagnostic.message
    assert Diagnostic.model_validate_json(diagnostic.model_dump_json()) == diagnostic
    assert spec.model_dump_json() == before


def test_incomplete_definition_is_distinct_from_invalid_operations() -> None:
    spec = definition([{"id": "r", "method": "regulator", "regulator_id": "W1"}])
    build_definition(spec)
    with pytest.raises(BuildError) as caught:
        validate_definition(spec)
    assert caught.value.diagnostic.code == "incomplete_document"
    assert caught.value.diagnostic.operation_id is None


def test_scope_and_shadowing_still_come_from_core() -> None:
    operations: list[dict[str, object]] = [
        {
            "id": "global",
            "method": "range_",
            "name": "level",
            "type": "Z",
            "location": "N1",
        },
        {"id": "reg", "method": "regulator", "regulator_id": "W1"},
        {
            "id": "local",
            "method": "range_",
            "name": "level",
            "type": "Z",
            "location": "N2",
        },
        {
            "id": "rule",
            "method": "rule",
            "type": "POS",
            "variable_value": {"ref": "global"},
        },
    ]
    with pytest.raises(BuildError, match="shadowed"):
        build_definition(definition(operations))
    operations[-1]["variable_value"] = {"ref": "local"}
    validate_definition(definition(operations))


def test_invalid_document_name_has_field_context() -> None:
    spec = DefinitionInput(name="bad\nname", operations=())
    with pytest.raises(BuildError) as caught:
        build_definition(spec)
    assert caught.value.diagnostic.field == "name"


def test_previous_regulator_locals_cannot_be_referenced() -> None:
    operations: list[dict[str, object]] = [
        {"id": "first", "method": "regulator", "regulator_id": "W1"},
        {
            "id": "local",
            "method": "range_",
            "name": "level",
            "type": "Z",
            "location": "N1",
        },
        {
            "id": "first_rule",
            "method": "rule",
            "type": "POS",
            "variable_value": {"ref": "local"},
        },
        {"id": "second", "method": "regulator", "regulator_id": "W2"},
        {
            "id": "second_rule",
            "method": "rule",
            "type": "POS",
            "variable_value": {"ref": "local"},
        },
    ]
    with pytest.raises(BuildError, match="current scope") as caught:
        build_definition(definition(operations))
    assert caught.value.diagnostic.operation_id == "second_rule"


def test_core_rejects_assignment_in_a_different_scope() -> None:
    spec = definition(
        [
            {"id": "v", "method": "declare_variable", "name": "v"},
            {
                "id": "initial",
                "method": "assign_variable",
                "target": {"ref": "v"},
                "operator": "=",
                "argument_1": 0,
            },
            {"id": "reg", "method": "regulator", "regulator_id": "W1"},
            {
                "id": "update",
                "method": "assign_variable",
                "target": {"ref": "v"},
                "operator": "=",
                "argument_1": 1,
            },
        ]
    )
    with pytest.raises(BuildError, match="creation scope") as caught:
        build_definition(spec)
    assert caught.value.diagnostic.operation_id == "update"


def test_forward_reference_is_not_resolved_by_later_definition() -> None:
    spec = definition(
        [
            {
                "id": "logic",
                "method": "logic",
                "name": "test",
                "operator": "NOT",
                "condition_1": {"ref": "later"},
            },
            {
                "id": "later",
                "method": "range_",
                "name": "level",
                "type": "Z",
                "location": "N1",
            },
        ]
    )
    with pytest.raises(BuildError) as caught:
        build_definition(spec)
    assert caught.value.diagnostic.code == "unknown_reference"


def test_four_conditions_and_if_operands_match_direct_calls() -> None:
    spec = definition(
        [
            {
                "id": "level",
                "method": "range_",
                "name": "level",
                "type": "Z",
                "location": "N1",
            },
            {
                "id": "logic",
                "method": "logic",
                "name": "any",
                "operator": "OR",
                "condition_1": {"ref": "level"},
                "condition_2": {"ref": "level"},
                "condition_3": {"ref": "level"},
                "condition_4": {"ref": "level"},
            },
            {"id": "v", "method": "declare_variable", "name": "v"},
            {
                "id": "if",
                "method": "assign_variable",
                "target": {"ref": "v"},
                "operator": "IF",
                "argument_1": {"ref": "logic"},
                "argument_2": 1,
                "argument_3": {"ref": "v"},
            },
            *closing_operations(),
        ]
    )
    direct = RTCCreator("Control")
    level = direct.range_("level", RangeType.LEVEL, "N1")
    condition = direct.logic("any", LogicOperator.OR, level, level, level, level)
    variable = direct.variable("v")
    direct.variable(variable, VariableOperator.IF, condition, 1, variable)
    direct.regulator("W1")
    direct.rule(RuleType.POSITION)
    assert build_definition(spec).render() == direct.render()
