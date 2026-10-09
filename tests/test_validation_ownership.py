from collections.abc import Callable
from datetime import time

import pytest

from rtc_infoworks_icm import RTCCreator, RTCValidationError
from rtc_infoworks_icm.elements.comment import Comment
from rtc_infoworks_icm.elements.controller import Controller, ControllerType
from rtc_infoworks_icm.elements.logic import Logic, LogicOperator
from rtc_infoworks_icm.elements.range import Range, RangeType, WeeklyTime
from rtc_infoworks_icm.elements.regulator import Regulator
from rtc_infoworks_icm.elements.rule import Rule, RuleType
from rtc_infoworks_icm.elements.table import Table, TableRow, TableType
from rtc_infoworks_icm.elements.variable import (
    Variable,
    VariableAssignment,
    VariableOperator,
)
from rtc_infoworks_icm.reference import Reference


def _error_message(action: Callable[[], object]) -> str:
    with pytest.raises(RTCValidationError) as error:
        action()
    return str(error.value)


def _with_source(action: Callable[[RTCCreator, Range], object]) -> object:
    rtc = RTCCreator("Control")
    source = rtc.range_("level", RangeType.LEVEL, "node.1")
    rtc.regulator("pump.1")
    return action(rtc, source)


@pytest.mark.parametrize("value", [True, float("inf"), float("nan"), 1e20])
def test_variable_model_owns_numeric_validation(value: float) -> None:
    direct = _error_message(
        lambda: VariableAssignment(Variable("value"), VariableOperator.ASSIGN, value)
    )
    public = _error_message(
        lambda: RTCCreator("Control").variable("value", VariableOperator.ASSIGN, value)
    )
    assert public == direct


@pytest.mark.parametrize("value", [True, float("inf"), float("nan"), 1e20])
def test_range_model_owns_numeric_validation(value: float) -> None:
    direct = _error_message(
        lambda: Range("level", RangeType.LEVEL, location="node.1", minimum=value)
    )
    public = _error_message(
        lambda: RTCCreator("Control").range_(
            "level", RangeType.LEVEL, "node.1", minimum=value
        )
    )
    assert public == direct


@pytest.mark.parametrize("value", [True, float("inf"), float("nan"), 1e20])
def test_table_row_model_owns_output_validation(value: float) -> None:
    direct = _error_message(lambda: TableRow(0, value))
    public = _error_message(
        lambda: _with_source(
            lambda rtc, source: rtc.table("curve", source, TableType.STEP, [(0, value)])
        )
    )
    assert public == direct


@pytest.mark.parametrize("weekday", [True, 0, 8])
def test_weekly_model_owns_weekday_validation(weekday: int) -> None:
    direct = _error_message(lambda: WeeklyTime(weekday, time(6)))
    public = _error_message(
        lambda: RTCCreator("Control").range_(
            "week", RangeType.TIME_REPEAT, minimum=(weekday, time(6))
        )
    )
    assert public == direct


def test_weekly_model_rejects_non_integer_weekday() -> None:
    with pytest.raises(RTCValidationError, match="must be an integer"):
        WeeklyTime(1.5, time(6))  # type: ignore[arg-type]


def test_weekly_model_rejects_non_time_value() -> None:
    with pytest.raises(RTCValidationError, match="must be a time value"):
        WeeklyTime(1, "06:00")  # type: ignore[arg-type]


def test_table_row_model_rejects_non_numeric_output() -> None:
    with pytest.raises(RTCValidationError, match="table output must be a number"):
        TableRow(0, "value")  # type: ignore[arg-type]


def test_reference_model_owns_target_validation() -> None:
    with pytest.raises(RTCValidationError, match="referenceable object"):
        RTCCreator("Control").rule(RuleType.SWITCH_ON, condition=123)  # type: ignore[arg-type]


def test_variable_model_rejects_missing_required_argument() -> None:
    with pytest.raises(RTCValidationError, match="argument 1 must be"):
        VariableAssignment(Variable("value"), VariableOperator.ASSIGN, None)  # type: ignore[arg-type]


def test_creator_leverages_variable_model_for_invalid_argument_type() -> None:
    with pytest.raises(RTCValidationError, match="argument 1 must be"):
        RTCCreator("Control").variable("value", VariableOperator.ASSIGN, [])  # type: ignore[arg-type]


def test_range_model_owns_variable_location_identifier_validation() -> None:
    direct = _error_message(
        lambda: Range("value", RangeType.VARIABLE, location="long-reference")
    )
    public = _error_message(
        lambda: RTCCreator("Control").range_(
            "value", RangeType.VARIABLE, location="long-reference"
        )
    )
    assert public == direct


_OPTION_CASES: list[
    tuple[Callable[[object], object], Callable[[object], object], str, str, object]
] = [
    (
        lambda value: VariableAssignment(Variable("value"), value, 1),  # type: ignore[arg-type]
        lambda value: RTCCreator("Control").variable("value", value, 1),  # type: ignore[arg-type]
        "operator",
        "=",
        VariableOperator.ASSIGN,
    ),
    (
        lambda value: Range("level", value, location="node.1"),  # type: ignore[arg-type]
        lambda value: RTCCreator("Control").range_("level", value, "node.1"),  # type: ignore[arg-type]
        "type",
        "Z",
        RangeType.LEVEL,
    ),
    (
        lambda value: Table(
            "curve",
            Reference(Range("level", RangeType.LEVEL, "node.1")),
            value,  # type: ignore[arg-type]
            (TableRow(0, 1),),
        ),  # type: ignore[arg-type]
        lambda value: _with_source(
            lambda rtc, source: rtc.table("curve", source, value, [(0, 1)])  # type: ignore[arg-type]
        ),  # type: ignore[arg-type]
        "type",
        "STEP",
        TableType.STEP,
    ),
    (
        lambda value: Logic(
            "high",
            value,  # type: ignore[arg-type]
            Reference(Range("level", RangeType.LEVEL, "node.1")),  # type: ignore[arg-type]
        ),  # type: ignore[arg-type]
        lambda value: _with_source(
            lambda rtc, source: rtc.logic("high", value, source)  # type: ignore[arg-type]
        ),  # type: ignore[arg-type]
        "operator",
        "NOT",
        LogicOperator.NOT,
    ),
    (
        lambda value: Controller("inc", value, 60),  # type: ignore[arg-type]
        lambda value: RTCCreator("Control").controller("inc", value, 60),  # type: ignore[arg-type]
        "type",
        "INC",
        ControllerType.INCREMENTAL,
    ),
    (
        lambda value: Rule(value),  # type: ignore[arg-type]
        lambda value: _with_source(lambda rtc, source: rtc.rule(value)),  # type: ignore[arg-type]
        "type",
        "POS",
        RuleType.POSITION,
    ),
]


@pytest.mark.parametrize("direct,public,attribute,code,expected", _OPTION_CASES)
def test_models_preserve_enum_members(
    direct: Callable[[object], object],
    public: Callable[[object], object],
    attribute: str,
    code: str,
    expected: object,
) -> None:
    assert getattr(direct(expected), attribute) is expected
    public(expected)


@pytest.mark.parametrize("direct,public,attribute,code,expected", _OPTION_CASES)
@pytest.mark.parametrize(
    "value", ["unknown", "", "pos", None, True, 1, [], ControllerType.PID]
)
def test_models_own_option_errors(
    direct: Callable[[object], object],
    public: Callable[[object], object],
    attribute: str,
    code: str,
    expected: object,
    value: object,
) -> None:
    if value is ControllerType.PID and expected is ControllerType.INCREMENTAL:
        value = RuleType.CONTROL
    direct_message = _error_message(lambda: direct(value))
    public_message = _error_message(lambda: public(value))
    assert "member" in direct_message
    assert public_message == direct_message
    assert "member" in _error_message(lambda: direct(code))
    assert "member" in _error_message(lambda: public(code))


def test_enum_options_enforce_model_specific_rules() -> None:
    with pytest.raises(RTCValidationError, match="requires argument 2"):
        VariableAssignment(Variable("value"), VariableOperator.ADD, 1)
    with pytest.raises(RTCValidationError, match="at least 2"):
        Logic(
            "high",
            LogicOperator.AND,
            Reference(Range("level", RangeType.LEVEL, "node.1")),
        )
    with pytest.raises(RTCValidationError, match="only used with control"):
        Rule(
            RuleType.POSITION,
            controller=Reference(Controller("inc", ControllerType.INCREMENTAL, 60)),
        )
    with pytest.raises(RTCValidationError, match="only used with PID"):
        Controller(
            "inc",
            ControllerType.INCREMENTAL,
            60,
            sensor=Reference(Range("level", RangeType.LEVEL, "node.1")),
        )


_TEXT_CASES: list[
    tuple[Callable[[object], object], Callable[[object], object], str]
] = [
    (
        lambda value: Comment(value),  # type: ignore[arg-type]
        lambda value: RTCCreator("Control").comment(value),  # type: ignore[arg-type]
        "comment text",
    ),
    (
        lambda value: Regulator(value),  # type: ignore[arg-type]
        lambda value: RTCCreator("Control").regulator(value),  # type: ignore[arg-type]
        "regulator ID",
    ),
    (
        lambda value: Range("level", RangeType.LEVEL, location=value),  # type: ignore[arg-type]
        lambda value: RTCCreator("Control").range_("level", RangeType.LEVEL, value),  # type: ignore[arg-type]
        "numeric range location",
    ),
    (
        lambda value: VariableAssignment(
            Variable("value"),
            VariableOperator.ASSIGN,
            1,
            measurement=value,  # type: ignore[arg-type]
        ),  # type: ignore[arg-type]
        lambda value: RTCCreator("Control").variable(
            "value",
            VariableOperator.ASSIGN,
            1,
            measurement=value,  # type: ignore[arg-type]
        ),
        "variable measurement",
    ),
    (
        lambda value: Table(
            "curve",
            Reference(Range("level", RangeType.LEVEL, "node.1")),
            TableType.STEP,
            (TableRow(0, 1),),
            output_measurement=value,  # type: ignore[arg-type]
        ),
        lambda value: _with_source(
            lambda rtc, source: rtc.table(
                "curve",
                source,
                TableType.STEP,
                [(0, 1)],
                output_measurement=value,  # type: ignore[arg-type]
            )
        ),
        "table output measurement",
    ),
]


@pytest.mark.parametrize("direct,public,field", _TEXT_CASES)
@pytest.mark.parametrize(
    "value",
    [123, True, [], b"text", Reference(Range("level", RangeType.LEVEL, "node.1"))],
)
def test_models_own_text_type_errors(
    direct: Callable[[object], object],
    public: Callable[[object], object],
    field: str,
    value: object,
) -> None:
    assert _error_message(lambda: direct(value)) == f"{field} must be text"
    assert _error_message(lambda: public(value)) == f"{field} must be text"
