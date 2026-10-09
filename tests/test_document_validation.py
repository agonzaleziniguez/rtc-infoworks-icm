from collections.abc import Callable
from datetime import datetime, time

import pytest

from rtc_infoworks_icm._document import (
    DocumentState,
    ReferenceableElement,
    RTCElement,
    validate_document,
)
from rtc_infoworks_icm.elements.comment import Comment
from rtc_infoworks_icm.elements.controller import Controller, ControllerType
from rtc_infoworks_icm.elements.logic import Logic, LogicOperator
from rtc_infoworks_icm.elements.range import Range, RangeType, WeeklyTime
from rtc_infoworks_icm.elements.regulator import Regulator
from rtc_infoworks_icm.elements.rule import Rule, RuleType
from rtc_infoworks_icm.elements.table import Table, TableRow, TableType
from rtc_infoworks_icm.elements.variable import Variable, VariableAssignment, VariableOperator
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


def test_document_accepts_global_and_local_definitions() -> None:
    level = Range("level", RangeType.LEVEL, "node.1")
    high = Logic("high", LogicOperator.NOT, Reference(level))
    validate_document(
        "Control",
        [
            level,
            Regulator("pump.1"),
            high,
            Rule(RuleType.POSITION, condition=Reference(high)),
            Regulator("pump.2"),
            Rule(RuleType.POSITION, condition=Reference(level)),
        ],
    )


def test_document_allows_local_shadowing_and_reuse_between_regulators() -> None:
    global_signal = Range("signal", RangeType.LEVEL, "node.1")
    local_signal = Variable("signal")
    next_signal = Range("signal", RangeType.DEPTH, "node.2")
    validate_document(
        "Control",
        [
            global_signal,
            Regulator("pump.1"),
            local_signal,
            VariableAssignment(local_signal, VariableOperator.ASSIGN, 1),
            Rule(RuleType.POSITION, variable_value=Reference(local_signal)),
            Regulator("pump.2"),
            next_signal,
            Rule(RuleType.POSITION, condition=Reference(next_signal)),
        ],
    )


def test_document_allows_repeated_and_self_referencing_variables() -> None:
    total = Variable("total")
    validate_document(
        "Control",
        [
            total,
            VariableAssignment(total, VariableOperator.ADD, Reference(total), 1),
            VariableAssignment(total, VariableOperator.MULTIPLY, Reference(total), 2),
            Regulator("pump.1"),
            Rule(RuleType.POSITION, variable_value=Reference(total)),
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


def test_section_completion_is_checked_before_transition_and_transactionally() -> None:
    empty = DocumentState()
    first = empty.adding([Regulator("pump.1")])

    with pytest.raises(RTCValidationError, match="duplicate regulator ID"):
        first.adding([Regulator("pump.1")])
    with pytest.raises(RTCValidationError, match="pump.1.*at least one rule"):
        first.adding([Regulator("pump.2")])

    completed_first = first.adding([Rule(RuleType.POSITION)])
    finished = completed_first.adding([Regulator("pump.2"), Rule(RuleType.POSITION)])
    finished.finish()


_SOURCE = Range("source", RangeType.LEVEL, "node.1")
_FACTORIES: tuple[Callable[[], ReferenceableElement], ...] = (
    lambda: Range("signal", RangeType.LEVEL, "node.1"),
    lambda: Logic("signal", LogicOperator.NOT, Reference(_SOURCE)),
    lambda: Table("signal", Reference(_SOURCE), TableType.STEP, (TableRow(0, 1),)),
    lambda: Controller("signal", ControllerType.INCREMENTAL, 60),
    lambda: Variable("signal"),
)


@pytest.mark.parametrize("first", _FACTORIES)
@pytest.mark.parametrize("second", _FACTORIES)
@pytest.mark.parametrize("local", [False, True])
def test_document_enforces_same_scope_name_policy(
    first: Callable[[], ReferenceableElement],
    second: Callable[[], ReferenceableElement],
    local: bool,
) -> None:
    elements: list[RTCElement] = [_SOURCE]
    if local:
        elements.append(Regulator("pump.1"))
    elements.extend((first(), second()))
    if not local:
        elements.append(Regulator("pump.1"))
    elements.append(Rule(RuleType.POSITION))
    with pytest.raises(RTCValidationError, match="duplicate definition"):
        validate_document("Control", elements)


@pytest.mark.parametrize("factory", _FACTORIES)
def test_document_allows_each_element_name_in_separate_scopes(
    factory: Callable[[], ReferenceableElement],
) -> None:
    validate_document(
        "Control",
        [
            _SOURCE,
            factory(),
            Regulator("pump.1"),
            factory(),
            Rule(RuleType.POSITION),
            Regulator("pump.2"),
            factory(),
            Rule(RuleType.POSITION),
        ],
    )


def _reference_surfaces(
    source: Range,
    controller: Controller,
    variable: Variable,
) -> list[RTCElement]:
    return [
        Logic("logic", LogicOperator.NOT, Reference(source)),
        Table("table", Reference(source), TableType.STEP, (TableRow(0, 1),)),
        VariableAssignment(variable, VariableOperator.ASSIGN, Reference(source)),
        Range("range", RangeType.VARIABLE, Reference(source)),
        Controller("pid", ControllerType.PID, 60, Reference(source)),
        Rule(RuleType.POSITION, condition=Reference(source)),
        Rule(RuleType.CONTROL, controller=Reference(controller)),
        Rule(RuleType.POSITION, variable_value=Reference(source)),
    ]


@pytest.mark.parametrize("surface", range(8))
@pytest.mark.parametrize("forward", [False, True])
def test_document_checks_every_reference_surface(surface: int, forward: bool) -> None:
    source = Range("source", RangeType.LEVEL, "node.1")
    controller = Controller("inc", ControllerType.INCREMENTAL, 60)
    variable = Variable("var")
    element = _reference_surfaces(source, controller, variable)[surface]
    elements: list[RTCElement] = [Regulator("pump.1"), variable, element]
    if forward:
        elements.extend((source, controller))
    elements.append(Rule(RuleType.POSITION))
    with pytest.raises(RTCValidationError, match="not yet declared"):
        validate_document("Control", elements)


@pytest.mark.parametrize("surface", range(8))
def test_document_rejects_leaked_local_targets(surface: int) -> None:
    source = Range("source", RangeType.LEVEL, "node.1")
    controller = Controller("inc", ControllerType.INCREMENTAL, 60)
    variable = Variable("var")
    element = _reference_surfaces(source, controller, variable)[surface]
    prefix: list[RTCElement] = [
        Regulator("pump.1"),
        source,
        controller,
        variable,
        VariableAssignment(variable, VariableOperator.ASSIGN, 1),
        Rule(RuleType.POSITION),
        Regulator("pump.2"),
    ]
    # An assignment to the old local identity is itself out of scope.
    with pytest.raises(RTCValidationError, match="scope"):
        validate_document("Control", [*prefix, element, Rule(RuleType.POSITION)])


@pytest.mark.parametrize("same_kind", [False, True])
def test_document_rejects_held_global_object_hidden_by_local(same_kind: bool) -> None:
    source = Range("signal", RangeType.LEVEL, "node.1")
    local = (
        Range("signal", RangeType.LEVEL, "node.2") if same_kind else Variable("signal")
    )
    with pytest.raises(RTCValidationError, match="shadowed"):
        validate_document(
            "Control",
            [
                source,
                Regulator("pump.1"),
                local,
                Rule(RuleType.POSITION, condition=Reference(source)),
            ],
        )


def test_document_rejects_equal_looking_foreign_identity() -> None:
    source = Range("signal", RangeType.LEVEL, "node.1")
    other = Range("signal", RangeType.LEVEL, "node.1")
    assert source != other
    with pytest.raises(RTCValidationError, match="foreign"):
        validate_document(
            "Control",
            [
                source,
                Regulator("pump.1"),
                Rule(RuleType.POSITION, condition=Reference(other)),
            ],
        )


def test_document_variable_self_reference_does_not_allow_other_forward_references() -> (
    None
):
    total, later = Variable("total"), Variable("later")
    with pytest.raises(RTCValidationError, match="'later'"):
        validate_document(
            "Control",
            [
                total,
                VariableAssignment(
                    total, VariableOperator.ADD, Reference(total), Reference(later)
                ),
                later,
                VariableAssignment(later, VariableOperator.ASSIGN, 1),
                Regulator("pump.1"),
                Rule(RuleType.POSITION),
            ],
        )


def test_document_registered_variable_still_requires_first_assignment() -> None:
    total, later = Variable("total"), Variable("later")
    with pytest.raises(RTCValidationError, match="first assignment"):
        validate_document(
            "Control",
            [
                total,
                later,
                VariableAssignment(total, VariableOperator.ASSIGN, Reference(later)),
                VariableAssignment(later, VariableOperator.ASSIGN, 1),
                Regulator("pump.1"),
                Rule(RuleType.POSITION),
            ],
        )


def test_document_rejects_unregistered_assignment_target() -> None:
    with pytest.raises(RTCValidationError, match="not registered"):
        validate_document(
            "Control",
            [
                VariableAssignment(Variable("value"), VariableOperator.ASSIGN, 1),
                Regulator("pump.1"),
                Rule(RuleType.POSITION),
            ],
        )


def test_document_global_variable_is_readable_but_not_updatable_locally() -> None:
    total = Variable("total")
    prefix: list[RTCElement] = [
        total,
        VariableAssignment(total, VariableOperator.ASSIGN, 1),
        Regulator("pump.1"),
    ]
    validate_document(
        "Control", [*prefix, Rule(RuleType.POSITION, variable_value=Reference(total))]
    )
    with pytest.raises(RTCValidationError, match="creation scope"):
        validate_document(
            "Control",
            [
                *prefix,
                VariableAssignment(total, VariableOperator.ASSIGN, 2),
                Rule(RuleType.POSITION),
            ],
        )


@pytest.mark.parametrize("name", [None, 1, True, [], b"title"])
def test_document_name_requires_text(name: object) -> None:
    with pytest.raises(RTCValidationError, match="document name must be text"):
        validate_document(name, [Regulator("pump.1"), Rule(RuleType.POSITION)])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "range_type",
    [
        RangeType.FLOW,
        RangeType.VELOCITY,
        RangeType.DEPTH,
        RangeType.LEVEL,
    ],
)
def test_constructor_accepts_supported_pid_sensor(range_type: RangeType) -> None:
    sensor = Range("sensor", range_type, "node.1")
    pid = Controller("pid", ControllerType.PID, 60, Reference(sensor))
    validate_document(
        "Control",
        [
            sensor,
            pid,
            Regulator("pump.1"),
            Rule(RuleType.CONTROL, controller=Reference(pid)),
        ],
    )


def test_constructor_rejects_unsupported_pid_sensor() -> None:
    sensor = Range("sensor", RangeType.RAINFALL, "subcatch")
    with pytest.raises(RTCValidationError, match="Q, V, Y, or Z"):
        Controller("pid", ControllerType.PID, 60, Reference(sensor))


@pytest.mark.parametrize("surface", range(7))
def test_constructor_rejects_wrong_reference_kind(surface: int) -> None:
    wrong = Reference(Controller("inc", ControllerType.INCREMENTAL, 60))
    factories: tuple[Callable[[], object], ...] = (
        lambda: Logic("logic", LogicOperator.NOT, wrong),  # type: ignore[arg-type]
        lambda: Table("table", wrong, TableType.STEP, (TableRow(0, 1),)),  # type: ignore[arg-type]
        lambda: VariableAssignment(Variable("var"), VariableOperator.ASSIGN, wrong),  # type: ignore[arg-type]
        lambda: Range("range", RangeType.VARIABLE, wrong),  # type: ignore[arg-type]
        lambda: Rule(RuleType.POSITION, condition=wrong),  # type: ignore[arg-type]
        lambda: Rule(RuleType.POSITION, variable_value=wrong),  # type: ignore[arg-type]
        lambda: Controller("pid", ControllerType.PID, 60, wrong),  # type: ignore[arg-type]
    )
    with pytest.raises(RTCValidationError, match="must reference"):
        factories[surface]()


def test_constructor_requires_controller_object_for_rule() -> None:
    with pytest.raises(RTCValidationError, match="must reference Controller"):
        Rule(RuleType.CONTROL, controller=Reference(Variable("var")))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "source",
    [
        Range("source", RangeType.LEVEL, "node.1"),
        Range("source", RangeType.TIME),
        Range("source", RangeType.LOCAL_CLOCK_TIME),
        Range("source", RangeType.TIME_REPEAT),
        Range("source", RangeType.LOCAL_CLOCK_TIME_REPEAT),
        Variable("source"),
    ],
)
@pytest.mark.parametrize(
    "value", [0, datetime(2026, 1, 1, 6), time(6), WeeklyTime(1, time(6))]
)
def test_constructor_checks_table_input_against_source(
    source: Range | Variable,
    value: int | datetime | time | WeeklyTime,
) -> None:
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
        table = Table("curve", Reference(source), TableType.STEP, (TableRow(value, 1),))
        elements: list[RTCElement] = [source]
        if isinstance(source, Variable):
            elements.append(VariableAssignment(source, VariableOperator.ASSIGN, 1))
        validate_document(
            "Control", [*elements, table, Regulator("pump.1"), Rule(RuleType.POSITION)]
        )
    else:
        with pytest.raises(RTCValidationError, match="table input must be"):
            Table("curve", Reference(source), TableType.STEP, (TableRow(value, 1),))


def test_chained_table_uses_numeric_output_of_time_table() -> None:
    source = Range("source", RangeType.TIME_REPEAT)
    daily = Table("daily", Reference(source), TableType.STEP, (TableRow(time(6), 1),))
    curve = Table("curve", Reference(daily), TableType.STEP, (TableRow(0, 2),))
    validate_document(
        "Control", [source, daily, curve, Regulator("pump.1"), Rule(RuleType.POSITION)]
    )
    with pytest.raises(RTCValidationError, match="numeric source"):
        Table("invalid", Reference(daily), TableType.STEP, (TableRow(time(7), 2),))
