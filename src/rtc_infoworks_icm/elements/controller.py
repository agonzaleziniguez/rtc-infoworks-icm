"""RTC controller model."""

from dataclasses import dataclass
from enum import StrEnum

from rtc_infoworks_icm._validation import (
    validate_finite,
    validate_identifier,
    validate_integer,
)
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference

_MEASUREMENT_INTERVAL_WIDTH = 5


class ControllerType(StrEnum):
    """Supported ways an RTC controller can drive a regulator."""

    INCREMENTAL = "INC"
    PID = "PID"
    FUZZY = "FUZZY"
    CENTAUR = "CENTAUR"


@dataclass(frozen=True, slots=True)
class Controller:
    """An indirect control loop that drives a regulator toward a setpoint."""

    name: str
    type: ControllerType
    measurement_interval: int
    sensor: Reference | None = None
    filter_coefficient: int | float = 0.0
    proportional: int | float = 0.0
    integral: int | float = 0.0
    differential: int | float = 0.0

    def __post_init__(self) -> None:
        validate_identifier(self.name, field="controller name")
        self._validate_measurement_interval()
        self._validate_pid_only_fields()

    def _validate_measurement_interval(self) -> None:
        value = self.measurement_interval
        validate_integer(value, field="controller measurement interval")
        if value <= 0:
            raise RTCValidationError(
                "controller measurement interval must be greater than zero"
            )
        if len(str(value)) > _MEASUREMENT_INTERVAL_WIDTH:
            raise RTCValidationError(
                "controller measurement interval does not fit the RTC field"
            )

    def _validate_pid_only_fields(self) -> None:
        is_pid = self.type is ControllerType.PID
        if self.sensor is not None and not is_pid:
            raise RTCValidationError("controller sensor is only used with PID type")

        pid_fields = (
            ("filter coefficient", self.filter_coefficient),
            ("proportional coefficient", self.proportional),
            ("integral coefficient", self.integral),
            ("differential coefficient", self.differential),
        )
        # PID coefficient width is a minimum padding width, not a size limit.
        # Longer values are serialized in full.
        for label, value in pid_fields:
            validate_finite(value, field=f"controller {label}")
            if not is_pid and value != 0.0:
                raise RTCValidationError(
                    f"controller {label} is only used with PID type"
                )
