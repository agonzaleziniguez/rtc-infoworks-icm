"""RTC rule model."""

from dataclasses import dataclass
from enum import StrEnum

from rtc_infoworks_icm._validation import validate_finite_number
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference

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
    condition: Reference | None = None
    controller: Reference | None = None
    fixed_value: int | float = 0.0
    variable_value: Reference | None = None

    def __post_init__(self) -> None:
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
        validate_finite_number(
            value,
            field="rule fixed value",
            width=_FIXED_VALUE_WIDTH,
            precision=precision,
        )
