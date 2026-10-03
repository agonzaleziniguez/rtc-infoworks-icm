from collections.abc import Callable
from datetime import time

import pytest

from rtc_infoworks_icm.elements.comment import Comment
from rtc_infoworks_icm.elements.controller import Controller, ControllerType
from rtc_infoworks_icm.elements.logic import Logic, LogicOperator
from rtc_infoworks_icm.elements.range import Range, RangeType, WeeklyTime
from rtc_infoworks_icm.elements.regulator import Regulator
from rtc_infoworks_icm.elements.rule import Rule, RuleType
from rtc_infoworks_icm.elements.table import Table, TableRow, TableType
from rtc_infoworks_icm.elements.variable import Variable, VariableOperator
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference

_OPTION_CASES: list[tuple[Callable[[object], object], object]] = [
    (lambda value: Variable("value", value, 1), VariableOperator.ASSIGN),  # type: ignore[arg-type]
    (lambda value: Range("level", value, "node.1"), RangeType.LEVEL),  # type: ignore[arg-type]
    (
        lambda value: Table("curve", Reference("level"), value, (TableRow(0, 1),)),  # type: ignore[arg-type]
        TableType.STEP,
    ),
    (lambda value: Logic("logic", value, Reference("level")), LogicOperator.NOT),  # type: ignore[arg-type]
    (lambda value: Controller("inc", value, 60), ControllerType.INCREMENTAL),  # type: ignore[arg-type]
    (lambda value: Rule(value), RuleType.POSITION),  # type: ignore[arg-type]
]


@pytest.mark.parametrize("construct,member", _OPTION_CASES)
@pytest.mark.parametrize("value", [None, True, 123, [], RuleType.CONTROL])
def test_models_require_their_own_enum(
    construct: Callable[[object], object], member: object, value: object
) -> None:
    if value is RuleType.CONTROL and member is RuleType.POSITION:
        value = ControllerType.PID
    with pytest.raises(RTCValidationError, match="must be a .* member"):
        construct(value)
    with pytest.raises(RTCValidationError, match="must be a .* member"):
        construct(str(member))
    construct(member)


_TEXT_CASES: list[tuple[Callable[[object], object], str]] = [
    (lambda value: Comment(value), "comment text"),  # type: ignore[arg-type]
    (lambda value: Regulator(value), "regulator ID"),  # type: ignore[arg-type]
    (lambda value: Reference(value), "reference name"),  # type: ignore[arg-type]
    (lambda value: Variable(value, VariableOperator.ASSIGN, 1), "variable name"),  # type: ignore[arg-type]
    (lambda value: Range("level", RangeType.LEVEL, value), "numeric range location"),  # type: ignore[arg-type]
    (
        lambda value: Variable("value", VariableOperator.ASSIGN, 1, measurement=value),  # type: ignore[arg-type]
        "variable measurement",
    ),
    (
        lambda value: Table(
            "curve",
            Reference("level"),
            TableType.STEP,
            (TableRow(0, 1),),
            output_measurement=value,  # type: ignore[arg-type]
        ),
        "table output measurement",
    ),
]


@pytest.mark.parametrize("construct,field", _TEXT_CASES)
@pytest.mark.parametrize("value", [123, True, [], b"text", Reference("level")])
def test_models_require_text(
    construct: Callable[[object], object], field: str, value: object
) -> None:
    with pytest.raises(RTCValidationError, match=f"^{field} must be text$"):
        construct(value)


_REFERENCE_CASES: list[tuple[Callable[[object], object], str]] = [
    (
        lambda value: Logic("logic", LogicOperator.NOT, value),  # type: ignore[arg-type]
        "logic condition 1",
    ),
    (
        lambda value: Logic("logic", LogicOperator.AND, Reference("one"), value),  # type: ignore[arg-type]
        "logic condition 2",
    ),
    (
        lambda value: Logic(
            "logic",
            LogicOperator.AND,
            Reference("one"),
            Reference("two"),
            value,  # type: ignore[arg-type]
        ),
        "logic condition 3",
    ),
    (
        lambda value: Logic(
            "logic",
            LogicOperator.AND,
            Reference("one"),
            Reference("two"),
            Reference("three"),
            value,  # type: ignore[arg-type]
        ),
        "logic condition 4",
    ),
    (
        lambda value: Rule(RuleType.CONTROL, condition=value),  # type: ignore[arg-type]
        "rule condition",
    ),
    (
        lambda value: Rule(RuleType.CONTROL, controller=value),  # type: ignore[arg-type]
        "rule controller",
    ),
    (
        lambda value: Rule(RuleType.CONTROL, variable_value=value),  # type: ignore[arg-type]
        "rule variable value",
    ),
    (
        lambda value: Controller("pid", ControllerType.PID, 60, sensor=value),  # type: ignore[arg-type]
        "controller sensor",
    ),
    (
        lambda value: Table("curve", value, TableType.STEP, (TableRow(0, 1),)),  # type: ignore[arg-type]
        "table input range",
    ),
]


@pytest.mark.parametrize("construct,field", _REFERENCE_CASES)
@pytest.mark.parametrize("value", ["level", 123, True, [], TableRow(0, 1)])
def test_models_require_typed_references(
    construct: Callable[[object], object], field: str, value: object
) -> None:
    with pytest.raises(RTCValidationError, match=f"^{field} must be a Reference$"):
        construct(value)


def test_logic_requires_first_condition() -> None:
    with pytest.raises(
        RTCValidationError, match="logic condition 1 must be a Reference"
    ):
        Logic("logic", LogicOperator.NOT, None)  # type: ignore[arg-type]


def test_table_requires_input_reference() -> None:
    with pytest.raises(
        RTCValidationError, match="table input range must be a Reference"
    ):
        Table("curve", None, TableType.STEP, (TableRow(0, 1),))  # type: ignore[arg-type]


@pytest.mark.parametrize("rows", [None, [], [TableRow(0, 1)], "rows", 123])
def test_table_requires_immutable_rows(rows: object) -> None:
    with pytest.raises(RTCValidationError, match="rows must be a tuple"):
        Table("curve", Reference("level"), TableType.STEP, rows)  # type: ignore[arg-type]


@pytest.mark.parametrize("row", [None, (0, 1), "row", 123, Reference("level")])
def test_table_requires_typed_rows(row: object) -> None:
    with pytest.raises(RTCValidationError, match="table row 2 must be a TableRow"):
        Table("curve", Reference("level"), TableType.STEP, (TableRow(0, 1), row))  # type: ignore[arg-type]


def test_models_preserve_valid_references_and_rows() -> None:
    reference = Reference("level")
    rows = (TableRow(0, 1),)
    assert Logic("logic", LogicOperator.NOT, reference).condition_1 is reference
    rule = Rule(
        RuleType.CONTROL,
        condition=reference,
        controller=reference,
        variable_value=reference,
    )
    assert rule.condition is reference
    assert rule.controller is reference
    assert rule.variable_value is reference
    assert (
        Controller("pid", ControllerType.PID, 60, sensor=reference).sensor is reference
    )
    table = Table("curve", reference, TableType.STEP, rows)
    assert table.input_range is reference
    assert table.rows is rows
    assert Rule(RuleType.POSITION).condition is None
    assert Controller("pid", ControllerType.PID, 60).sensor is None


@pytest.mark.parametrize("weekday", [True, 1.5, "1"])
def test_weekly_time_requires_integer_weekday(weekday: object) -> None:
    with pytest.raises(RTCValidationError, match="weekday must be an integer"):
        WeeklyTime(weekday, time(6))  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [None, "06:00", 6])
def test_weekly_time_requires_time(value: object) -> None:
    with pytest.raises(RTCValidationError, match="must be a time value"):
        WeeklyTime(1, value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [None, "value", [], True])
def test_variable_requires_valid_first_argument(value: object) -> None:
    with pytest.raises(RTCValidationError, match="argument 1 must be"):
        Variable("value", VariableOperator.ASSIGN, value)  # type: ignore[arg-type]


@pytest.mark.parametrize("position", [2, 3])
def test_variable_requires_valid_optional_argument_types(position: int) -> None:
    with pytest.raises(RTCValidationError, match=f"argument {position} must be"):
        Variable(
            "value",
            VariableOperator.IF,
            1,
            [] if position == 2 else 2,  # type: ignore[arg-type]
            [] if position == 3 else 3,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("value", [None, "value", [], True])
def test_table_row_requires_numeric_output(value: object) -> None:
    with pytest.raises(RTCValidationError, match="table output must be a number"):
        TableRow(0, value)  # type: ignore[arg-type]
