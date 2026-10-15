"""Translate an ordered definition into public core calls, without retaining state."""

from datetime import datetime, time

from rtc_infoworks_icm import (
    Controller,
    Logic,
    Range,
    RTCCreator,
    RTCValidationError,
    Table,
    Variable,
)
from rtc_infoworks_icm_mcp.models import (
    AddComment,
    AddController,
    AddLogic,
    AddRange,
    AddTable,
    ArgumentInput,
    AssignVariable,
    BeginRegulator,
    BoundInput,
    CalendarInput,
    DeclareVariable,
    DefinitionInput,
    Diagnostic,
    NumericInput,
    Operation,
    ReferenceInput,
    WeeklyTimeInput,
)

type ReferencedElement = Range | Table | Variable | Logic | Controller
type ValueElement = Range | Table | Variable | Logic
type Bound = int | float | datetime | time | tuple[int, time]


class BuildError(Exception):
    """An expected construction failure with structured request context."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(diagnostic.message)


def build_definition(definition: DefinitionInput) -> RTCCreator:
    """Build an open creator; incomplete definitions are allowed.

    Each call owns fresh objects. No candidate escapes on construction failure.
    Call validate_definition or creator.render() for a complete-document check.
    """
    try:
        creator = RTCCreator(definition.name)
    except RTCValidationError as error:
        raise BuildError(
            Diagnostic(code="invalid_document", message=str(error), field="name")
        ) from error

    elements_by_id: dict[str, ReferencedElement] = {}
    seen: set[str] = set()
    for index, operation in enumerate(definition.operations):
        if operation.id in seen:
            raise BuildError(
                Diagnostic(
                    code="duplicate_operation_id",
                    message=f"Operation ID {operation.id!r} is already used.",
                    operation_id=operation.id,
                    operation_index=index,
                    field="id",
                )
            )
        try:
            element = _apply(creator, operation, elements_by_id)
        except BuildError as error:
            raise BuildError(
                error.diagnostic.model_copy(
                    update={"operation_id": operation.id, "operation_index": index}
                )
            ) from error
        except RTCValidationError as error:
            raise BuildError(
                Diagnostic(
                    code="invalid_document",
                    message=str(error),
                    operation_id=operation.id,
                    operation_index=index,
                )
            ) from error
        seen.add(operation.id)
        if element is not None:
            elements_by_id[operation.id] = element
    return creator


def validate_definition(definition: DefinitionInput) -> None:
    """Build and check completeness without closing or writing the document."""
    creator = build_definition(definition)
    try:
        creator.validate()
    except RTCValidationError as error:
        raise BuildError(
            Diagnostic(code="incomplete_document", message=str(error))
        ) from error


def _bound(value: BoundInput | None) -> Bound | None:
    if value is None:
        return None
    if isinstance(value, NumericInput):
        return value.value
    if isinstance(value, CalendarInput):
        return value.to_python()
    if isinstance(value, WeeklyTimeInput):
        return value.weekday, value.to_python()
    return value.to_python()


def _resolve[T: ReferencedElement](
    reference: ReferenceInput,
    elements_by_id: dict[str, ReferencedElement],
    allowed: type[T] | tuple[type[T], ...],
    field: str,
) -> T:
    try:
        target = elements_by_id[reference.ref]
    except KeyError as error:
        raise BuildError(
            Diagnostic(
                code="unknown_reference",
                message=(
                    f"Reference {reference.ref!r} is not an earlier "
                    "referenceable operation."
                ),
                field=field,
            )
        ) from error
    if not isinstance(target, allowed):
        raise BuildError(
            Diagnostic(
                code="wrong_reference_kind",
                message=(
                    f"Reference {reference.ref!r} has an unsupported kind for {field}."
                ),
                field=field,
            )
        )
    return target


def _optional[T: ReferencedElement](
    reference: ReferenceInput | None,
    elements_by_id: dict[str, ReferencedElement],
    allowed: type[T] | tuple[type[T], ...],
    field: str,
) -> T | None:
    return (
        None
        if reference is None
        else _resolve(reference, elements_by_id, allowed, field)
    )


def _argument(
    argument: ArgumentInput | None,
    elements_by_id: dict[str, ReferencedElement],
    field: str,
) -> int | float | ValueElement | None:
    if isinstance(argument, ReferenceInput):
        return _resolve(
            argument, elements_by_id, (Range, Table, Variable, Logic), field
        )
    return argument


def _apply(
    creator: RTCCreator,
    operation: Operation,
    elements_by_id: dict[str, ReferencedElement],
) -> ReferencedElement | None:
    if isinstance(operation, AddComment):
        creator.comment(operation.text)
    elif isinstance(operation, AddRange):
        location = operation.location
        if isinstance(location, ReferenceInput):
            location = _resolve(
                location, elements_by_id, (Range, Table, Variable, Logic), "location"
            )
        return creator.range_(
            operation.name,
            operation.type,
            location,
            _bound(operation.minimum),
            _bound(operation.maximum),
            operation.distance,
        )
    elif isinstance(operation, AddTable):
        rows: list[tuple[Bound, int | float]] = []
        for row in operation.rows:
            value = _bound(row.input)
            assert value is not None
            rows.append((value, row.output))
        return creator.table(
            operation.name,
            _resolve(
                operation.input_range,
                elements_by_id,
                (Range, Table, Variable),
                "input_range",
            ),
            operation.type,
            rows,
            operation.output_measurement,
        )
    elif isinstance(operation, DeclareVariable):
        return creator.variable(operation.name)
    elif isinstance(operation, AssignVariable):
        argument_1 = _argument(operation.argument_1, elements_by_id, "argument_1")
        assert argument_1 is not None
        creator.variable(
            _resolve(operation.target, elements_by_id, Variable, "target"),
            operation.operator,
            argument_1,
            _argument(operation.argument_2, elements_by_id, "argument_2"),
            _argument(operation.argument_3, elements_by_id, "argument_3"),
            operation.measurement,
        )
    elif isinstance(operation, AddLogic):
        return creator.logic(
            operation.name,
            operation.operator,
            _resolve(
                operation.condition_1, elements_by_id, (Range, Logic), "condition_1"
            ),
            _optional(
                operation.condition_2, elements_by_id, (Range, Logic), "condition_2"
            ),
            _optional(
                operation.condition_3, elements_by_id, (Range, Logic), "condition_3"
            ),
            _optional(
                operation.condition_4, elements_by_id, (Range, Logic), "condition_4"
            ),
        )
    elif isinstance(operation, AddController):
        return creator.controller(
            operation.name,
            operation.type,
            operation.measurement_interval,
            _optional(operation.sensor, elements_by_id, Range, "sensor"),
            operation.filter_coefficient,
            operation.proportional,
            operation.integral,
            operation.differential,
        )
    elif isinstance(operation, BeginRegulator):
        creator.regulator(
            operation.regulator_id,
            operation.initial,
            operation.threshold,
            operation.positive_rate,
            operation.negative_rate,
            operation.override_other_control,
        )
    else:
        creator.rule(
            operation.type,
            _optional(operation.condition, elements_by_id, (Range, Logic), "condition"),
            _optional(operation.controller, elements_by_id, Controller, "controller"),
            operation.fixed_value,
            _optional(
                operation.variable_value,
                elements_by_id,
                (Range, Table, Variable),
                "variable_value",
            ),
        )
    return None
