"""RTC table model."""

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from typing import TypeIs

from rtc_infoworks_icm._validation import (
    validate_finite_number,
    validate_formatted_number_width,
    validate_identifier,
    validate_option,
    validate_text,
)
from rtc_infoworks_icm.elements.range import RangeBound, WeeklyTime, compute_repeat_order_key
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference, validate_reference

_MAX_MEASUREMENT_LENGTH = 7


class TableType(StrEnum):
    """Interpolation types for an RTC table."""

    LINEAR = "LINEAR"
    STEP = "STEP"


@dataclass(frozen=True, slots=True)
class TableRow:
    """A single input/output pair in an RTC table."""

    x: RangeBound
    y: int | float

    def __post_init__(self) -> None:
        _validate_x(self.x)
        _validate_y(self.y)


@dataclass(frozen=True, slots=True)
class Table:
    """A lookup that translates a measured input into an output value.

    Rows must be an immutable tuple of validated TableRow instances.
    """

    name: str
    input_range: Reference
    type: TableType
    rows: tuple[TableRow, ...]
    output_measurement: str | None = None

    def __post_init__(self) -> None:
        validate_option(self.type, TableType, field="table type")
        validate_identifier(self.name, field="table name")
        validate_reference(self.input_range, field="table input range")
        _validate_rows(self.rows)
        self._validate_output_measurement()
        if not self.rows:
            raise RTCValidationError("table requires at least one row")
        _validate_row_order(self.rows)

    def _validate_output_measurement(self) -> None:
        measurement = self.output_measurement
        if measurement is None:
            return
        validate_text(measurement, field="table output measurement")
        if not measurement.strip():
            raise RTCValidationError("table output measurement cannot be empty")
        if len(measurement) > _MAX_MEASUREMENT_LENGTH:
            raise RTCValidationError(
                "table output measurement cannot exceed "
                f"{_MAX_MEASUREMENT_LENGTH} characters"
            )


def _validate_rows(value: object) -> None:
    if not _is_tuple(value):
        raise RTCValidationError("table rows must be a tuple of TableRow instances")
    for position, row in enumerate(value, start=1):
        if not isinstance(row, TableRow):
            raise RTCValidationError(f"table row {position} must be a TableRow")


def _is_tuple(value: object) -> TypeIs[tuple[object, ...]]:
    return isinstance(value, tuple)


def _validate_x(value: RangeBound) -> None:
    if isinstance(value, WeeklyTime):
        return
    if isinstance(value, (datetime, time)):
        if value.utcoffset() is not None:
            raise RTCValidationError("table input must not include a timezone")
        return
    validate_finite_number(value, field="table input")
    validate_formatted_number_width(value, field="table input", width=14, precision=3)


def _validate_y(value: int | float) -> None:
    validate_finite_number(value, field="table output")
    validate_formatted_number_width(value, field="table output", width=14, precision=3)


def _classify(value: RangeBound) -> str:
    if isinstance(value, datetime):
        return "datetime"
    if isinstance(value, WeeklyTime):
        return "weekly_time"
    if isinstance(value, time):
        return "time"
    return "number"


def _compute_ordering_key(value: RangeBound) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (time, WeeklyTime)):
        return compute_repeat_order_key(value)
    return float(value)


def _validate_row_order(rows: tuple[TableRow, ...]) -> None:
    previous = rows[0]
    for row in rows[1:]:
        if _classify(row.x) != _classify(previous.x):
            raise RTCValidationError("table rows must use a single input type")
        if _compute_ordering_key(row.x) <= _compute_ordering_key(previous.x):
            raise RTCValidationError(
                "table rows must be in strictly ascending input order"
            )
        previous = row
