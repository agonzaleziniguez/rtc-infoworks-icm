"""RTC variable model."""

import math
from dataclasses import dataclass
from enum import StrEnum

from rtc_infoworks_icm._validation import validate_identifier
from rtc_infoworks_icm.exceptions import RTCValidationError

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


@dataclass(frozen=True, slots=True)
class Reference:
    """The name of another RTC element used as an input."""

    name: str

    def __post_init__(self) -> None:
        validate_identifier(self.name, field="reference name")


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
            if isinstance(argument, bool):
                raise RTCValidationError(
                    f"variable argument {position} cannot be a boolean"
                )
            if isinstance(argument, (int, float)):
                if not math.isfinite(argument):
                    raise RTCValidationError(
                        f"variable argument {position} must be finite"
                    )
                if len(f"{argument:.5f}") > 14:
                    raise RTCValidationError(
                        f"variable argument {position} does not fit the RTC field"
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
