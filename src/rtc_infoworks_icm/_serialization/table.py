"""Serialization of RTC tables."""

from datetime import datetime, time

from rtc_infoworks_icm._serialization.fields import (
    serialize_datetime_field,
    serialize_number_field,
    serialize_text_field,
    serialize_time_field,
)
from rtc_infoworks_icm.elements.range import WeeklyTime
from rtc_infoworks_icm.elements.table import Table, TableRow


def serialize_table(table: Table) -> str:
    """Serialize a validated RTC table."""
    measurement = table.output_measurement
    header = " ".join(
        (
            serialize_text_field("TABLE", width=10),
            serialize_text_field(table.name, width=10),
            serialize_text_field(table.input_range.name, width=10),
            serialize_text_field(measurement.upper() if measurement else None, width=7),
            serialize_text_field(table.type.value, width=6),
        )
    )
    entries = (_serialize_row(row) for row in table.rows)
    return "\n".join((header, *entries)) + "\n"


def _serialize_row(row: TableRow) -> str:
    fields = (
        serialize_text_field("TABLEENTRY", width=10),
        serialize_text_field(None, width=10),
        serialize_text_field(None, width=10),
        _serialize_x(row.x),
        serialize_number_field(row.y, width=14, precision=3),
    )
    return " ".join(fields)


def _serialize_x(value: int | float | datetime | time | WeeklyTime) -> str:
    if isinstance(value, datetime):
        return serialize_datetime_field(value)
    if isinstance(value, (time, WeeklyTime)):
        return serialize_time_field(value)
    return serialize_number_field(value, width=14, precision=3)
