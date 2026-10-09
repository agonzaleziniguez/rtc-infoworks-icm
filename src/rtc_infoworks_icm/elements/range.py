"""RTC range model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from typing import TYPE_CHECKING

from rtc_infoworks_icm._validation import (
    validate_finite_number,
    validate_formatted_number_width,
    validate_identifier,
    validate_integer,
    validate_nonempty_text,
    validate_option,
    validate_single_line_text,
)
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import (
    Reference,
    ReferenceKind,
    ReferenceTarget,
    ValueType,
    validate_reference,
)

if TYPE_CHECKING:
    from rtc_infoworks_icm.elements.logic import Logic
    from rtc_infoworks_icm.elements.table import Table
    from rtc_infoworks_icm.elements.variable import Variable

_MIN_WEEKDAY = 1
_MAX_WEEKDAY = 7


@dataclass(frozen=True, slots=True)
class WeeklyTime:
    """A time of day paired with a day of the week.

    Used for weekly-repeat time ranges/tables, where the RTC format encodes
    the weekday (1=Monday ... 7=Sunday) alongside the time of day.
    """

    weekday: int
    time: time

    def __post_init__(self) -> None:
        validate_integer(self.weekday, field="weekly time weekday")
        _validate_weekly_time(self.time)
        if not _MIN_WEEKDAY <= self.weekday <= _MAX_WEEKDAY:
            raise RTCValidationError(
                f"weekly time weekday must be between {_MIN_WEEKDAY} and {_MAX_WEEKDAY}"
            )
        if self.time.utcoffset() is not None:
            raise RTCValidationError("weekly time must not include a timezone")


def _validate_weekly_time(value: object) -> None:
    if not isinstance(value, time):
        raise RTCValidationError("weekly time must be a time value")


type RangeBound = int | float | datetime | time | WeeklyTime


class RangeType(StrEnum):
    """Supported RTC measurement range types."""

    FLOW = "Q"
    VELOCITY = "V"
    DEPTH = "Y"
    LEVEL = "Z"
    RAINFALL = "R"
    RAINFALL_INTENSITY = "RINT"
    TIME = "T"
    TIME_REPEAT = "TR"
    LOCAL_CLOCK_TIME = "LCT"
    LOCAL_CLOCK_TIME_REPEAT = "LCTR"
    FLOW_CHANGE = "DQ"
    DEPTH_CHANGE = "DY"
    LEVEL_CHANGE = "DZ"
    REGULATOR_STATE = "REG"
    ADAPTIVE_PUMP_CONTROL = "APC"
    PUMP_STATE = "PUMP"
    VARIABLE = "VAR"
    SF1_CONCENTRATION = "CSF1"
    SF2_CONCENTRATION = "CSF2"
    DISSOLVED_AMMONIUM = "CNH4D"
    BOD_SF1 = "CBOD1"
    BOD_SF2 = "CBOD2"
    BOD_DISSOLVED = "CBODD"
    BOD_TOTAL = "CBODT"
    COD_SF1 = "CCOD1"
    COD_SF2 = "CCOD2"
    COD_DISSOLVED = "CCODD"
    COD_TOTAL = "CCODT"
    TKN_SF1 = "CTKN1"
    TKN_SF2 = "CTKN2"
    TKN_DISSOLVED = "CTKND"
    TKN_TOTAL = "CTKNT"
    TPH_SF1 = "CTPH1"
    TPH_SF2 = "CTPH2"
    TPH_DISSOLVED = "CTPHD"
    TPH_TOTAL = "CTPHT"
    PL1_SF1 = "CPL11"
    PL1_SF2 = "CPL12"
    PL1_DISSOLVED = "CPL1D"
    PL1_TOTAL = "CPL1T"
    PL2_SF1 = "CPL21"
    PL2_SF2 = "CPL22"
    PL2_DISSOLVED = "CPL2D"
    PL2_TOTAL = "CPL2T"
    PL3_SF1 = "CPL31"
    PL3_SF2 = "CPL32"
    PL3_DISSOLVED = "CPL3D"
    PL3_TOTAL = "CPL3T"
    PL4_SF1 = "CPL41"
    PL4_SF2 = "CPL42"
    PL4_DISSOLVED = "CPL4D"
    PL4_TOTAL = "CPL4T"


_DATETIME_TYPES = frozenset({RangeType.TIME, RangeType.LOCAL_CLOCK_TIME})
_REPEATING_TIME_TYPES = frozenset(
    {RangeType.TIME_REPEAT, RangeType.LOCAL_CLOCK_TIME_REPEAT}
)
_TIME_TYPES = _DATETIME_TYPES | _REPEATING_TIME_TYPES


@dataclass(frozen=True, slots=True, eq=False)
class Range(ReferenceTarget):
    """A condition that is true while a measured value is within its bounds."""

    name: str
    type: RangeType
    location: str | Reference[Range | Table | Variable | Logic] | None = None
    minimum: RangeBound | None = None
    maximum: RangeBound | None = None
    distance: int | float = 0.0

    def __post_init__(self) -> None:
        validate_option(self.type, RangeType, field="range type")
        validate_identifier(self.name, field="range name")
        self._validate_distance()

        if self.type in _TIME_TYPES:
            self._validate_time_range()
        else:
            self._validate_numeric_range()

    @property
    def reference_kind(self) -> ReferenceKind:
        return ReferenceKind.RANGE

    @property
    def value_type(self) -> ValueType:
        if self.type in _DATETIME_TYPES:
            return ValueType.DATETIME
        if self.type in _REPEATING_TIME_TYPES:
            return ValueType.REPEATING_TIME
        return ValueType.NUMBER

    def _validate_distance(self) -> None:
        validate_finite_number(self.distance, field="range distance")
        validate_formatted_number_width(
            self.distance, field="range distance", width=7, precision=1
        )

    def _validate_time_range(self) -> None:
        if self.location is not None:
            raise RTCValidationError("time range does not use a location")
        if self.distance != 0:
            raise RTCValidationError("time range does not use a distance")

        if self.type in _DATETIME_TYPES:
            minimum = self._validate_datetime_bound(self.minimum, field="minimum")
            maximum = self._validate_datetime_bound(self.maximum, field="maximum")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise RTCValidationError("range minimum cannot exceed maximum")
        else:
            minimum = self._validate_repeat_bound(self.minimum, field="minimum")
            maximum = self._validate_repeat_bound(self.maximum, field="maximum")
            if (
                minimum is not None
                and maximum is not None
                and compute_repeat_order_key(minimum)
                > compute_repeat_order_key(maximum)
            ):
                raise RTCValidationError("range minimum cannot exceed maximum")

    def _validate_datetime_bound(
        self,
        value: RangeBound | None,
        *,
        field: str,
    ) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise RTCValidationError(f"time range {field} must be a datetime value")
        if value.utcoffset() is not None:
            raise RTCValidationError(f"time range {field} must not include a timezone")
        return value

    def _validate_repeat_bound(
        self,
        value: RangeBound | None,
        *,
        field: str,
    ) -> time | WeeklyTime | None:
        if value is None:
            return None
        if isinstance(value, WeeklyTime):
            return value
        if not isinstance(value, time):
            raise RTCValidationError(
                f"time range {field} must be a time or weekly time value"
            )
        if value.utcoffset() is not None:
            raise RTCValidationError(f"time range {field} must not include a timezone")
        return value

    def _validate_numeric_range(self) -> None:
        if self.location is None:
            raise RTCValidationError("numeric range location cannot be empty")
        if self.type is RangeType.VARIABLE:
            validate_reference(
                self.location,
                field="variable range location",
                allowed=(
                    ReferenceKind.RANGE,
                    ReferenceKind.TABLE,
                    ReferenceKind.VARIABLE,
                    ReferenceKind.LOGIC,
                ),
            )
        else:
            location = validate_nonempty_text(
                self.location, field="numeric range location"
            )
            message = "numeric range location cannot contain quotes or newlines"
            validate_single_line_text(
                location, field="numeric range location", error_message=message
            )
            if '"' in location:
                raise RTCValidationError(message)
        if self.type is RangeType.VARIABLE and self.distance != 0:
            raise RTCValidationError("variable range does not use a distance")

        minimum = self._validate_numeric_bound(self.minimum, field="minimum")
        maximum = self._validate_numeric_bound(self.maximum, field="maximum")

        if minimum is not None and maximum is not None and minimum > maximum:
            raise RTCValidationError("range minimum cannot exceed maximum")

    def _validate_numeric_bound(
        self,
        value: RangeBound | None,
        *,
        field: str,
    ) -> int | float | None:
        if value is None:
            return None
        if not isinstance(value, (int, float)):
            raise RTCValidationError(f"numeric range {field} must be a number")
        validate_finite_number(value, field=f"numeric range {field}")
        validate_formatted_number_width(
            value, field=f"numeric range {field}", width=14, precision=4
        )
        return value


def compute_repeat_order_key(value: time | WeeklyTime) -> float:
    """Compute a comparable key for a repeat-time bound (daily or weekly)."""
    weekday, time_of_day = (
        (0, value)
        if isinstance(value, time)
        else (
            value.weekday,
            value.time,
        )
    )
    seconds = (
        (time_of_day.hour * 3600)
        + (time_of_day.minute * 60)
        + time_of_day.second
        + (time_of_day.microsecond / 1_000_000)
    )
    return (weekday * 86400) + seconds
