"""Serialization of RTC ranges."""

from datetime import datetime, time

from rtc_infoworks_icm._serialization.fields import (
    serialize_datetime_field,
    serialize_number_field,
    serialize_text_field,
    serialize_time_field,
)
from rtc_infoworks_icm.elements.range import Range


def serialize_range(range_: Range) -> str:
    """Serialize a validated RTC range."""
    location = _serialize_location(range_.location)
    minimum = _serialize_bound(range_.minimum)
    maximum = _serialize_bound(range_.maximum)

    fields = (
        serialize_text_field("RANGE", width=10),
        serialize_text_field(range_.name, width=10),
        serialize_text_field(range_.type.value, width=5),
        location,
        serialize_number_field(range_.distance, width=7, precision=1),
        minimum,
        maximum,
    )
    return " ".join(fields) + "\n"


def _serialize_location(location: str | None) -> str:
    if location is None:
        return serialize_text_field(None, width=10)
    if len(location) <= 10:
        return serialize_text_field(location, width=10)
    return f'"{location}"'


def _serialize_bound(value: int | float | datetime | time | None) -> str:
    if isinstance(value, datetime):
        return serialize_datetime_field(value)
    if isinstance(value, time):
        return serialize_time_field(value)
    return serialize_number_field(value, width=14, precision=4)
