"""Serialization fields shared by RTC elements."""

from datetime import datetime, time

from rtc_infoworks_icm.elements.range import WeeklyTime
from rtc_infoworks_icm.reference import Reference


def serialize_text_field(value: str | None, *, width: int) -> str:
    """Serialize validated text as a right-aligned field."""
    return (" " * width) if value is None else value.rjust(width)


def serialize_number_field(
    value: int | float | None,
    *,
    width: int,
    precision: int,
) -> str:
    """Serialize a validated number as a right-aligned field."""
    return " " * width if value is None else f"{value:.{precision}f}".rjust(width)


def serialize_reference_field(value: Reference | None, *, width: int) -> str:
    """Serialize an optional reference as a right-aligned name field."""
    return serialize_text_field(value.name if value is not None else None, width=width)


def serialize_datetime_field(value: datetime) -> str:
    """Serialize a date-time value as a 14-character RTC date field."""
    return value.strftime("%d%m%Y%H%M%S")


def serialize_time_field(value: time | WeeklyTime) -> str:
    """Serialize a repeat-time value as a 14-character RTC date field.

    A plain time of day leaves the day/month/year digits as zero (the
    "daily" RTC convention). A `WeeklyTime` encodes its weekday (1-7) in
    the day digits and leaves month/year as zero (the "weekly" convention).
    """
    if isinstance(value, WeeklyTime):
        return f"{value.weekday:02d}000000{value.time:%H%M%S}"
    return f"00000000{value:%H%M%S}"
