"""RTC table model."""

import math
from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum

from rtc_infoworks_icm._validation import validate_identifier
from rtc_infoworks_icm.elements.range import RangeBound
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference

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
    """A lookup that translates a measured input into an output value."""

    name: str
    input_range: Reference
    type: TableType
    rows: tuple[TableRow, ...]
    output_measurement: str | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.name, field="table name")
        self._validate_output_measurement()
        if not self.rows:
            raise RTCValidationError("table requires at least one row")
        _validate_row_order(self.rows)

    def _validate_output_measurement(self) -> None:
        measurement = self.output_measurement
        if measurement is None:
            return
        if not measurement.strip():
            raise RTCValidationError("table output measurement cannot be empty")
        if len(measurement) > _MAX_MEASUREMENT_LENGTH:
            raise RTCValidationError(
                "table output measurement cannot exceed "
                f"{_MAX_MEASUREMENT_LENGTH} characters"
            )


def _validate_x(value: RangeBound) -> None:
    if isinstance(value, (datetime, time)):
        if value.utcoffset() is not None:
            raise RTCValidationError("table input must not include a timezone")
        return
    _validate_number(value, field="input")


def _validate_y(value: int | float) -> None:
    _validate_number(value, field="output")


def _validate_number(value: int | float, *, field: str) -> None:
    if isinstance(value, bool):
        raise RTCValidationError(f"table {field} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise RTCValidationError(f"table {field} must be finite")
    if len(f"{value:.3f}") > 14:
        raise RTCValidationError(f"table {field} does not fit the RTC field")


def _classify(value: RangeBound) -> str:
    if isinstance(value, datetime):
        return "datetime"
    if isinstance(value, time):
        return "time"
    return "number"


def _compute_ordering_key(value: RangeBound) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, time):
        seconds = (value.hour * 3600) + (value.minute * 60) + value.second
        return seconds + (value.microsecond / 1_000_000)
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
