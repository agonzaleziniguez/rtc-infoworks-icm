"""RTC rule model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from rtc_infoworks_icm._validation import (
    validate_finite_number,
    validate_formatted_number_width,
    validate_option,
)
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference, ReferenceKind, validate_reference

if TYPE_CHECKING:
    from rtc_infoworks_icm.elements.controller import Controller
    from rtc_infoworks_icm.elements.logic import Logic
    from rtc_infoworks_icm.elements.range import Range
    from rtc_infoworks_icm.elements.table import Table
    from rtc_infoworks_icm.elements.variable import Variable

_FIXED_VALUE_WIDTH = 8
_FIXED_VALUE_PRECISION = 4
# RTC represents a zero fixed value with 6 decimal places instead of 4,
# to match the field format ICM expects. Confirmed required by the format.
_ZERO_FIXED_VALUE_PRECISION = 6


class RuleType(StrEnum):
    """Supported ways an RTC rule can control a regulator."""

    CONTROL = "CTRL"
    POSITION = "POS"
    SWITCH_ON = "ON"
    SWITCH_OFF = "OFF"


@dataclass(frozen=True, slots=True)
class Rule:
    """A setpoint that takes effect for a regulator while its condition holds."""

    type: RuleType
    condition: Reference[Range | Logic] | None = None
    controller: Reference[Controller] | None = None
    fixed_value: int | float = 0.0
    variable_value: Reference[Range | Table | Variable] | None = None

    def __post_init__(self) -> None:
        validate_option(self.type, RuleType, field="rule type")
        for label, value, allowed in (
            ("condition", self.condition, (ReferenceKind.RANGE, ReferenceKind.LOGIC)),
            ("controller", self.controller, (ReferenceKind.CONTROLLER,)),
            (
                "variable value",
                self.variable_value,
                (ReferenceKind.RANGE, ReferenceKind.TABLE, ReferenceKind.VARIABLE),
            ),
        ):
            if value is not None:
                validate_reference(value, field=f"rule {label}", allowed=allowed)
        self._validate_fixed_value()
        if self.controller is not None and self.type is not RuleType.CONTROL:
            raise RTCValidationError(
                "rule controller is only used with control-type rules"
            )

    def _validate_fixed_value(self) -> None:
        value = self.fixed_value
        precision = (
            _ZERO_FIXED_VALUE_PRECISION if value == 0.0 else _FIXED_VALUE_PRECISION
        )
        validate_finite_number(value, field="rule fixed value")
        validate_formatted_number_width(
            value,
            field="rule fixed value",
            width=_FIXED_VALUE_WIDTH,
            precision=precision,
        )
