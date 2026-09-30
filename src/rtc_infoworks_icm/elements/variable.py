"""RTC variable model."""

from dataclasses import dataclass
from enum import StrEnum

from rtc_infoworks_icm._validation import validate_finite_number, validate_identifier
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference

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


type VariableArgument = int | float | Reference


@dataclass(frozen=True, slots=True)
class Variable:
    """A value calculated from constants or other RTC elements."""

    name: str
    operator: VariableOperator
    argument_1: VariableArgument
    argument_2: VariableArgument | None = None
    argument_3: VariableArgument | None = None
    measurement: str | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.name, field="variable name")
        if self.measurement is not None and not self.measurement.strip():
            raise RTCValidationError("variable measurement cannot be empty")
        if (
            self.measurement is not None
            and len(self.measurement) > _MAX_MEASUREMENT_LENGTH
        ):
            raise RTCValidationError(
                "variable measurement cannot exceed "
                f"{_MAX_MEASUREMENT_LENGTH} characters"
            )

        arguments = (self.argument_1, self.argument_2, self.argument_3)
        for position, argument in enumerate(arguments, start=1):
            if isinstance(argument, (int, float)):
                validate_finite_number(
                    argument,
                    field=f"variable argument {position}",
                    width=14,
                    precision=5,
                )

        if self.operator is VariableOperator.ASSIGN:
            self._require_empty_arguments(2, 3)
        elif self.operator in {
            VariableOperator.ADD,
            VariableOperator.SUBTRACT,
            VariableOperator.DIVIDE,
            VariableOperator.MULTIPLY,
        }:
            self._require_argument(2)
            self._require_empty_arguments(3)
        elif self.operator is VariableOperator.IF:
            self._require_argument(2)
            self._require_argument(3)

    def _require_argument(self, position: int) -> None:
        argument = self.argument_2 if position == 2 else self.argument_3
        if argument is None:
            raise RTCValidationError(
                f"{self.operator.name.lower()} variable requires argument {position}"
            )

    def _require_empty_arguments(self, *positions: int) -> None:
        for position in positions:
            argument = self.argument_2 if position == 2 else self.argument_3
            if argument is not None:
                raise RTCValidationError(
                    f"{self.operator.name.lower()} variable does not use "
                    f"argument {position}"
                )
