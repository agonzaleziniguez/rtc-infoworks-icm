from datetime import datetime, time

import pytest

from rtc_infoworks_icm._document import ReferenceableElement, RTCElement, validate_document
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


def test_document_accepts_global_and_local_definitions() -> None:
    validate_document(
        "Control",
        [
            Range("level", RangeType.LEVEL, location="node.1"),
            Regulator("pump.1"),
            Logic("high", LogicOperator.NOT, Reference("level")),
            Rule(RuleType.POSITION, condition=Reference("high")),
            Regulator("pump.2"),
            Rule(RuleType.POSITION, condition=Reference("level")),
        ],
    )


def test_document_allows_local_shadowing_and_reuse_between_regulators() -> None:
    validate_document(
        "Control",
        [
            Range("signal", RangeType.LEVEL, location="node.1"),
            Regulator("pump.1"),
            Variable("signal", VariableOperator.ASSIGN, 1),
            Rule(RuleType.POSITION, variable_value=Reference("signal")),
            Regulator("pump.2"),
            Range("signal", RangeType.DEPTH, location="node.2"),
            Rule(RuleType.POSITION, condition=Reference("signal")),
        ],
    )


def test_document_allows_repeated_and_self_referencing_variables() -> None:
    validate_document(
        "Control",
        [
            Variable("total", VariableOperator.ADD, Reference("total"), 1),
            Variable("total", VariableOperator.MULTIPLY, Reference("total"), 2),
            Regulator("pump.1"),
            Rule(RuleType.POSITION, variable_value=Reference("total")),
        ],
    )


@pytest.mark.parametrize(
    "elements",
    [
        [],
        [Comment("Only a comment")],
        [Regulator("pump.1")],
        [Rule(RuleType.POSITION)],
        [Regulator("pump.1"), Regulator("pump.2"), Rule(RuleType.POSITION)],
        [Regulator("pump.1"), Rule(RuleType.POSITION), Regulator("pump.2")],
        [
            Regulator("pump.1"),
            Rule(RuleType.POSITION),
            Regulator("pump.1"),
            Rule(RuleType.POSITION),
        ],
    ],
)
def test_document_rejects_invalid_sections(elements: list[RTCElement]) -> None:
    with pytest.raises(RTCValidationError):
        validate_document("Control", elements)


@pytest.mark.parametrize(
    "definition",
    [
        Range("signal", RangeType.LEVEL, location="node.1"),
        Variable("signal", VariableOperator.ASSIGN, 1),
        Logic("signal", LogicOperator.NOT, Reference("signal")),
        Controller("signal", ControllerType.INCREMENTAL, 60),
    ],
)
def test_document_rejects_duplicate_names(definition: RTCElement) -> None:
    with pytest.raises(RTCValidationError, match="duplicate definition"):
        validate_document(
            "Control",
            [
                Range("signal", RangeType.LEVEL, location="node.1"),
                definition,
                Regulator("pump.1"),
                Rule(RuleType.POSITION),
            ],
        )


@pytest.mark.parametrize(
    "element",
    [
        Logic("logic", LogicOperator.NOT, Reference("missing")),
        Table("table", Reference("missing"), TableType.LINEAR, (TableRow(0, 1),)),
        Variable("var", VariableOperator.ASSIGN, Reference("missing")),
        Range("range", RangeType.VARIABLE, location="missing"),
        Controller("pid", ControllerType.PID, 60, sensor=Reference("missing")),
        Rule(RuleType.POSITION, condition=Reference("missing")),
        Rule(RuleType.CONTROL, controller=Reference("missing")),
        Rule(RuleType.POSITION, variable_value=Reference("missing")),
    ],
)
def test_document_checks_every_reference_surface(element: RTCElement) -> None:
    with pytest.raises(RTCValidationError, match="not yet declared"):
        validate_document(
            "Control", [Regulator("pump.1"), element, Rule(RuleType.POSITION)]
        )


def test_document_rejects_forward_reference() -> None:
    with pytest.raises(RTCValidationError, match="not yet declared"):
        validate_document(
            "Control",
            [
                Regulator("pump.1"),
                Rule(RuleType.POSITION, condition=Reference("later")),
                Range("later", RangeType.LEVEL, location="node.1"),
            ],
        )


def test_document_does_not_leak_local_definitions() -> None:
    with pytest.raises(RTCValidationError, match="current scope"):
        validate_document(
            "Control",
            [
                Regulator("pump.1"),
                Range("local", RangeType.LEVEL, location="node.1"),
                Rule(RuleType.POSITION),
                Regulator("pump.2"),
                Rule(RuleType.POSITION, condition=Reference("local")),
            ],
        )


def test_document_does_not_fall_back_past_wrong_type_local_shadow() -> None:
    with pytest.raises(RTCValidationError, match="not Variable"):
        validate_document(
            "Control",
            [
                Range("signal", RangeType.LEVEL, location="node.1"),
                Regulator("pump.1"),
                Variable("signal", VariableOperator.ASSIGN, 1),
                Rule(RuleType.POSITION, condition=Reference("signal")),
            ],
        )


@pytest.mark.parametrize(
    "element",
    [
        Logic("logic", LogicOperator.NOT, Reference("controller")),
        Table("table", Reference("controller"), TableType.LINEAR, (TableRow(0, 1),)),
        Variable("var", VariableOperator.ASSIGN, Reference("controller")),
        Range("range", RangeType.VARIABLE, location="controller"),
        Rule(RuleType.POSITION, condition=Reference("controller")),
        Rule(RuleType.POSITION, variable_value=Reference("controller")),
    ],
)
def test_document_rejects_wrong_reference_kind(element: RTCElement) -> None:
    with pytest.raises(RTCValidationError, match="not Controller"):
        validate_document(
            "Control",
            [
                Controller("controller", ControllerType.INCREMENTAL, 60),
                Regulator("pump.1"),
                element,
                Rule(RuleType.POSITION),
            ],
        )


def test_document_rejects_non_controller_rule_controller() -> None:
    with pytest.raises(RTCValidationError, match="must reference Controller"):
        validate_document(
            "Control",
            [
                Variable("var", VariableOperator.ASSIGN, 1),
                Regulator("pump.1"),
                Rule(RuleType.CONTROL, controller=Reference("var")),
            ],
        )


@pytest.mark.parametrize(
    "range_type",
    [RangeType.FLOW, RangeType.VELOCITY, RangeType.DEPTH, RangeType.LEVEL],
)
def test_document_accepts_supported_pid_sensor(range_type: RangeType) -> None:
    validate_document(
        "Control",
        [
            Range("sensor", range_type, location="node.1"),
            Controller("pid", ControllerType.PID, 60, sensor=Reference("sensor")),
            Regulator("pump.1"),
            Rule(RuleType.CONTROL, controller=Reference("pid")),
        ],
    )


def test_document_rejects_unsupported_pid_sensor_range_type() -> None:
    with pytest.raises(RTCValidationError, match="Q, V, Y, or Z"):
        validate_document(
            "Control",
            [
                Range("sensor", RangeType.RAINFALL, location="subcatchment"),
                Controller("pid", ControllerType.PID, 60, sensor=Reference("sensor")),
                Regulator("pump.1"),
                Rule(RuleType.CONTROL, controller=Reference("pid")),
            ],
        )


_NAMED_ELEMENTS: tuple[ReferenceableElement, ...] = (
    Range("signal", RangeType.LEVEL, location="node.1"),
    Logic("signal", LogicOperator.NOT, Reference("source")),
    Table("signal", Reference("source"), TableType.STEP, (TableRow(0, 1),)),
    Controller("signal", ControllerType.INCREMENTAL, 60),
    Variable("signal", VariableOperator.ASSIGN, 1),
)


@pytest.mark.parametrize("first", _NAMED_ELEMENTS)
@pytest.mark.parametrize("second", _NAMED_ELEMENTS)
@pytest.mark.parametrize("local", [False, True])
def test_document_enforces_same_scope_name_policy(
    first: ReferenceableElement, second: ReferenceableElement, local: bool
) -> None:
    elements: list[RTCElement] = [Range("source", RangeType.LEVEL, location="node.1")]
    if local:
        elements.append(Regulator("pump.1"))
    elements.extend((first, second))
    if not local:
        elements.append(Regulator("pump.1"))
    elements.append(Rule(RuleType.POSITION))
    if isinstance(first, Variable) and isinstance(second, Variable):
        validate_document("Control", elements)
    else:
        with pytest.raises(RTCValidationError, match="duplicate definition"):
            validate_document("Control", elements)


@pytest.mark.parametrize("element", _NAMED_ELEMENTS)
def test_document_allows_each_element_name_in_separate_scopes(
    element: ReferenceableElement,
) -> None:
    validate_document(
        "Control",
        [
            Range("source", RangeType.LEVEL, location="node.1"),
            element,
            Regulator("pump.1"),
            element,
            Rule(RuleType.POSITION),
            Regulator("pump.2"),
            element,
            Rule(RuleType.POSITION),
        ],
    )


def test_document_variable_self_reference_does_not_allow_other_forward_references() -> (
    None
):
    with pytest.raises(RTCValidationError, match="'later'"):
        validate_document(
            "Control",
            [
                Variable(
                    "total",
                    VariableOperator.ADD,
                    Reference("total"),
                    Reference("later"),
                ),
                Variable("later", VariableOperator.ASSIGN, 1),
                Regulator("pump.1"),
                Rule(RuleType.POSITION),
            ],
        )


def test_document_rejects_self_reference_for_other_elements() -> None:
    with pytest.raises(RTCValidationError, match="not yet declared"):
        validate_document(
            "Control",
            [
                Logic("logic", LogicOperator.NOT, Reference("logic")),
                Regulator("pump.1"),
                Rule(RuleType.POSITION),
            ],
        )


@pytest.mark.parametrize("name", [None, 1, True, [], b"title"])
def test_document_name_requires_text(name: object) -> None:
    with pytest.raises(RTCValidationError, match="document name must be text"):
        validate_document(name, [Regulator("pump.1"), Rule(RuleType.POSITION)])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "source",
    [
        Range("source", RangeType.LEVEL, location="node.1"),
        Range("source", RangeType.TIME),
        Range("source", RangeType.LOCAL_CLOCK_TIME),
        Range("source", RangeType.TIME_REPEAT),
        Range("source", RangeType.LOCAL_CLOCK_TIME_REPEAT),
        Variable("source", VariableOperator.ASSIGN, 1),
    ],
)
@pytest.mark.parametrize(
    "value", [0, datetime(2026, 1, 1, 6), time(6), WeeklyTime(1, time(6))]
)
def test_document_checks_table_input_against_source(
    source: Range | Variable, value: int | datetime | time | WeeklyTime
) -> None:
    elements: list[RTCElement] = [
        source,
        Table("curve", Reference("source"), TableType.STEP, (TableRow(value, 1),)),
        Regulator("pump.1"),
        Rule(RuleType.POSITION),
    ]
    if isinstance(source, Range) and source.type in {
        RangeType.TIME,
        RangeType.LOCAL_CLOCK_TIME,
    }:
        valid = isinstance(value, datetime)
    elif isinstance(source, Range) and source.type in {
        RangeType.TIME_REPEAT,
        RangeType.LOCAL_CLOCK_TIME_REPEAT,
    }:
        valid = isinstance(value, (time, WeeklyTime))
    else:
        valid = isinstance(value, int)
    if valid:
        validate_document("Control", elements)
    else:
        with pytest.raises(RTCValidationError, match="table input must be"):
            validate_document("Control", elements)


def test_document_chained_table_uses_numeric_output_of_time_table() -> None:
    validate_document(
        "Control",
        [
            Range("source", RangeType.TIME_REPEAT),
            Table(
                "daily", Reference("source"), TableType.STEP, (TableRow(time(6), 1),)
            ),
            Table("curve", Reference("daily"), TableType.STEP, (TableRow(0, 2),)),
            Regulator("pump.1"),
            Rule(RuleType.POSITION),
        ],
    )


def test_document_rejects_time_input_when_source_is_another_table() -> None:
    with pytest.raises(RTCValidationError, match="numeric source"):
        validate_document(
            "Control",
            [
                Range("source", RangeType.TIME_REPEAT),
                Table(
                    "daily",
                    Reference("source"),
                    TableType.STEP,
                    (TableRow(time(6), 1),),
                ),
                Table(
                    "curve", Reference("daily"), TableType.STEP, (TableRow(time(7), 2),)
                ),
                Regulator("pump.1"),
                Rule(RuleType.POSITION),
            ],
        )


def test_document_table_compatibility_uses_local_source_before_global() -> None:
    with pytest.raises(RTCValidationError, match="numeric source"):
        validate_document(
            "Control",
            [
                Range("source", RangeType.TIME_REPEAT),
                Regulator("pump.1"),
                Variable("source", VariableOperator.ASSIGN, 1),
                Table(
                    "curve",
                    Reference("source"),
                    TableType.STEP,
                    (TableRow(time(6), 1),),
                ),
                Rule(RuleType.POSITION),
            ],
        )
