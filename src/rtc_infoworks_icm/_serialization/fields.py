"""Serialization fields shared by RTC elements."""

from datetime import datetime, time


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


def serialize_datetime_field(value: datetime) -> str:
    """Serialize a date-time value as a 14-character RTC date field."""
    return value.strftime("%d%m%Y%H%M%S")


def serialize_time_field(value: time) -> str:
    """Serialize a time-of-day value as a 14-character RTC date field."""
    return f"00000000{value:%H%M%S}"
