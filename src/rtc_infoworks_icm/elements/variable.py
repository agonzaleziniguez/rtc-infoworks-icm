"""RTC variable model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from rtc_infoworks_icm._validation import (
    validate_finite_number,
    validate_formatted_number_width,
    validate_identifier,
    validate_nonempty_text,
    validate_option,
)
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import (
    Reference,
    ReferenceKind,
    ReferenceTarget,
    ValueType,
    is_reference,
    validate_reference,
)

if TYPE_CHECKING:
    from rtc_infoworks_icm.elements.logic import Logic
    from rtc_infoworks_icm.elements.range import Range
    from rtc_infoworks_icm.elements.table import Table

_MAX_MEASUREMENT_LENGTH = 7


class VariableOperator(StrEnum):
    """Supported operations for an RTC variable."""

    ASSIGN = "="
    ADD = "+"
    SUBTRACT = "-"
    DIVIDE = "/"
    MULTIPLY = "*"
    IF = "IF"
    TIMER = "TIMER"


type VariableArgument = int | float | Reference[Range | Table | Variable | Logic]


@dataclass(frozen=True, slots=True, eq=False)
class Variable(ReferenceTarget):
    """A persistent numeric Variable; creating it does not emit an RTC record."""

    name: str

    def __post_init__(self) -> None:
        validate_identifier(self.name, field="variable name")

    @property
    def reference_kind(self) -> ReferenceKind:
        return ReferenceKind.VARIABLE

    @property
    def value_type(self) -> ValueType:
        return ValueType.NUMBER


@dataclass(frozen=True, slots=True)
class VariableAssignment:
    """One ordered operation; the target identity holds no simulation value."""

    target: Variable
    operator: VariableOperator
    argument_1: VariableArgument
    argument_2: VariableArgument | None = None
    argument_3: VariableArgument | None = None
    measurement: str | None = None

    def __post_init__(self) -> None:
        _validate_variable_target(self.target)
        validate_variable_operation(
            self.operator,
            (self.argument_1, self.argument_2, self.argument_3),
            self.measurement,
        )

    @property
    def name(self) -> str:
        return self.target.name


def _validate_variable_target(value: object) -> None:
    if not isinstance(value, Variable):
        raise RTCValidationError("variable assignment target must be a Variable")


def validate_variable_operation(
    operator: VariableOperator,
    arguments: tuple[object, object, object],
    measurement: str | None,
) -> None:
    """Validate the operator, operands, and per-record measurement."""
    validate_option(operator, VariableOperator, field="variable operator")
    if measurement is not None:
        validate_nonempty_text(measurement, field="variable measurement")
        if len(measurement) > _MAX_MEASUREMENT_LENGTH:
            raise RTCValidationError(
                "variable measurement cannot exceed "
                f"{_MAX_MEASUREMENT_LENGTH} characters"
            )

    for position, argument in enumerate(arguments, start=1):
        if argument is None and position != 1:
            continue
        if not isinstance(argument, (int, float)) and not is_reference(argument):
            raise RTCValidationError(
                f"variable argument {position} must be a number or reference"
            )
        if isinstance(argument, (int, float)):
            validate_finite_number(argument, field=f"variable argument {position}")
            validate_formatted_number_width(
                argument, field=f"variable argument {position}", width=14, precision=5
            )
        else:
            validate_reference(
                argument,
                field=f"variable argument {position}",
                allowed=(
                    ReferenceKind.RANGE,
                    ReferenceKind.TABLE,
                    ReferenceKind.VARIABLE,
                    ReferenceKind.LOGIC,
                ),
            )

    required: tuple[int, ...] = ()
    unused: tuple[int, ...] = ()
    if operator is VariableOperator.ASSIGN:
        unused = (2, 3)
    elif operator in {
        VariableOperator.ADD,
        VariableOperator.SUBTRACT,
        VariableOperator.DIVIDE,
        VariableOperator.MULTIPLY,
    }:
        required, unused = (2,), (3,)
    elif operator is VariableOperator.IF:
        required = (2, 3)
    for position in required:
        if arguments[position - 1] is None:
            raise RTCValidationError(
                f"{operator.name.lower()} variable requires argument {position}"
            )
    for position in unused:
        if arguments[position - 1] is not None:
            raise RTCValidationError(
                f"{operator.name.lower()} variable does not use argument {position}"
            )
