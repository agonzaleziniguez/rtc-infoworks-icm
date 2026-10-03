"""Validation of ordered RTC document contents."""

from collections.abc import Sequence
from datetime import datetime, time

from rtc_infoworks_icm._validation import validate_nonempty_text, validate_single_line_text
from rtc_infoworks_icm.elements.comment import Comment
from rtc_infoworks_icm.elements.controller import Controller
from rtc_infoworks_icm.elements.logic import Logic
from rtc_infoworks_icm.elements.range import Range, RangeType, WeeklyTime
from rtc_infoworks_icm.elements.regulator import Regulator
from rtc_infoworks_icm.elements.rule import Rule
from rtc_infoworks_icm.elements.table import Table
from rtc_infoworks_icm.elements.variable import Variable
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference

type RTCElement = (
    Comment | Controller | Logic | Range | Regulator | Rule | Table | Variable
)
type ReferenceableElement = Controller | Logic | Range | Table | Variable

_CONDITION_TYPES = (Range, Logic)
_VALUE_TYPES = (Range, Table, Variable, Logic)
_SETPOINT_TYPES = (Range, Table, Variable)
_SENSOR_TYPES = frozenset(
    {RangeType.FLOW, RangeType.VELOCITY, RangeType.DEPTH, RangeType.LEVEL}
)
_DATETIME_TYPES = frozenset({RangeType.TIME, RangeType.LOCAL_CLOCK_TIME})
_REPEATING_TIME_TYPES = frozenset(
    {RangeType.TIME_REPEAT, RangeType.LOCAL_CLOCK_TIME_REPEAT}
)


def validate_document(name: str, elements: Sequence[RTCElement]) -> None:
    """Validate declarations, references, and regulator sections in file order.

    Names share a namespace within each scope. Only Variable assignments may
    repeat a name there; other repetitions and cross-type collisions are
    conservatively rejected. Local names may shadow global names, and separate
    regulator sections may reuse names.
    """
    validate_document_name(name)

    global_definitions: dict[str, ReferenceableElement] = {}
    local_definitions: dict[str, ReferenceableElement] = {}
    regulator_ids: set[str] = set()
    regulator: Regulator | None = None
    rule_count = 0

    for element in elements:
        if isinstance(element, Comment):
            continue
        if isinstance(element, Regulator):
            if regulator is not None:
                _require_rules(regulator, rule_count)
            if element.regulator_id in regulator_ids:
                raise RTCValidationError(
                    f"duplicate regulator ID {element.regulator_id!r}"
                )
            regulator_ids.add(element.regulator_id)
            regulator = element
            local_definitions = {}
            rule_count = 0
            continue
        definitions = global_definitions if regulator is None else local_definitions
        if isinstance(element, Rule):
            if regulator is None:
                raise RTCValidationError("rule must belong to a regulator section")
            rule_count += 1
        else:
            _validate_definition_name(element, definitions)

        _validate_references(element, global_definitions, local_definitions)
        if not isinstance(element, Rule):
            definitions[element.name] = element

    if regulator is None:
        raise RTCValidationError("document requires at least one regulator")
    _require_rules(regulator, rule_count)


def validate_document_name(name: str) -> None:
    """Validate the document title independently of its contents."""
    validate_nonempty_text(name, field="document name")
    validate_single_line_text(name, field="document name")


def _validate_definition_name(
    element: ReferenceableElement,
    definitions: dict[str, ReferenceableElement],
) -> None:
    existing = definitions.get(element.name)
    if existing is None:
        return
    if isinstance(existing, Variable) and isinstance(element, Variable):
        return
    raise RTCValidationError(f"duplicate definition name {element.name!r}")


def _require_rules(regulator: Regulator, count: int) -> None:
    if count == 0:
        raise RTCValidationError(
            f"regulator {regulator.regulator_id!r} requires at least one rule"
        )


def _require_reference(
    reference: Reference,
    *,
    field: str,
    global_definitions: dict[str, ReferenceableElement],
    local_definitions: dict[str, ReferenceableElement],
    allowed: tuple[type[ReferenceableElement], ...],
) -> ReferenceableElement:
    definition = local_definitions.get(reference.name)
    if definition is None:
        definition = global_definitions.get(reference.name)
    if definition is None:
        raise RTCValidationError(
            f"{field} references undefined or not yet declared "
            f"element {reference.name!r} in the current scope"
        )
    if not isinstance(definition, allowed):
        expected = ", ".join(kind.__name__ for kind in allowed)
        raise RTCValidationError(
            f"{field} must reference {expected}, not {type(definition).__name__}"
        )
    return definition


def _validate_references(
    element: ReferenceableElement | Rule,
    global_definitions: dict[str, ReferenceableElement],
    local_definitions: dict[str, ReferenceableElement],
) -> None:
    def require(
        reference: Reference,
        field: str,
        allowed: tuple[type[ReferenceableElement], ...],
    ) -> ReferenceableElement:
        return _require_reference(
            reference,
            field=field,
            global_definitions=global_definitions,
            local_definitions=local_definitions,
            allowed=allowed,
        )

    if isinstance(element, Range):
        if element.type is RangeType.VARIABLE and element.location is not None:
            require(
                Reference(element.location), "variable range location", _VALUE_TYPES
            )
    elif isinstance(element, Logic):
        for position, condition in enumerate(
            (
                element.condition_1,
                element.condition_2,
                element.condition_3,
                element.condition_4,
            ),
            start=1,
        ):
            if condition is not None:
                require(condition, f"logic condition {position}", _CONDITION_TYPES)
    elif isinstance(element, Table):
        source = require(element.input_range, "table input", _SETPOINT_TYPES)
        _validate_table_input_type(element, source)
    elif isinstance(element, Variable):
        for position, argument in enumerate(
            (element.argument_1, element.argument_2, element.argument_3), start=1
        ):
            if isinstance(argument, Reference):
                # A variable exists with an initial value of zero, so it may
                # read its own value even in its first assignment.
                if argument.name != element.name:
                    require(argument, f"variable argument {position}", _VALUE_TYPES)
    elif isinstance(element, Controller):
        if element.sensor is not None:
            sensor = require(element.sensor, "controller sensor", (Range,))
            if isinstance(sensor, Range) and sensor.type not in _SENSOR_TYPES:
                raise RTCValidationError(
                    "controller sensor must reference a Q, V, Y, or Z range"
                )
    else:
        if element.condition is not None:
            require(element.condition, "rule condition", _CONDITION_TYPES)
        if element.controller is not None:
            require(element.controller, "rule controller", (Controller,))
        if element.variable_value is not None:
            require(element.variable_value, "rule variable value", _SETPOINT_TYPES)


def _validate_table_input_type(table: Table, source: ReferenceableElement) -> None:
    value = table.rows[0].x
    if isinstance(source, Range) and source.type in _DATETIME_TYPES:
        if not isinstance(value, datetime):
            raise RTCValidationError("table input must be datetime for a time range")
    elif isinstance(source, Range) and source.type in _REPEATING_TIME_TYPES:
        if not isinstance(value, (time, WeeklyTime)):
            raise RTCValidationError(
                "table input must be time or weekly time for a repeating time range"
            )
    elif not isinstance(value, (int, float)):
        raise RTCValidationError("table input must be numeric for a numeric source")
