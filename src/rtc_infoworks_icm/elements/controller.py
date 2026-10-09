"""RTC controller model."""

from dataclasses import dataclass
from enum import StrEnum

from rtc_infoworks_icm._validation import (
    validate_finite_number,
    validate_identifier,
    validate_integer,
    validate_option,
)
from rtc_infoworks_icm.elements.range import Range, RangeType
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import (
    Reference,
    ReferenceKind,
    ReferenceTarget,
    validate_reference,
)

_MEASUREMENT_INTERVAL_WIDTH = 5


class ControllerType(StrEnum):
    """Supported ways an RTC controller can drive a regulator."""

    INCREMENTAL = "INC"
    PID = "PID"
    FUZZY = "FUZZY"
    CENTAUR = "CENTAUR"


@dataclass(frozen=True, slots=True, eq=False)
class Controller(ReferenceTarget):
    """An indirect control loop that drives a regulator toward a setpoint."""

    name: str
    type: ControllerType
    measurement_interval: int
    sensor: Reference[Range] | None = None
    filter_coefficient: int | float = 0.0
    proportional: int | float = 0.0
    integral: int | float = 0.0
    differential: int | float = 0.0

    def __post_init__(self) -> None:
        validate_option(self.type, ControllerType, field="controller type")
        validate_identifier(self.name, field="controller name")
        if self.sensor is not None:
            validate_reference(
                self.sensor, field="controller sensor", allowed=(ReferenceKind.RANGE,)
            )
            _validate_pid_sensor(self.sensor.target)
        self._validate_measurement_interval()
        self._validate_pid_only_fields()

    @property
    def reference_kind(self) -> ReferenceKind:
        return ReferenceKind.CONTROLLER

    @property
    def value_type(self) -> None:
        return None

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
            validate_finite_number(value, field=f"controller {label}")
            if not is_pid and value != 0.0:
                raise RTCValidationError(
                    f"controller {label} is only used with PID type"
                )


def _validate_pid_sensor(value: object) -> None:
    if not isinstance(value, Range) or value.type not in {
        RangeType.FLOW,
        RangeType.VELOCITY,
        RangeType.DEPTH,
        RangeType.LEVEL,
    }:
        raise RTCValidationError(
            "controller sensor must reference a Q, V, Y, or Z range"
        )
