from datetime import datetime, time

from rtc_infoworks_icm._serialization.range import serialize_range
from rtc_infoworks_icm.elements.range import Range, RangeType, WeeklyTime


def test_serialize_numeric_range() -> None:
    range_ = Range(
        "level",
        RangeType.LEVEL,
        location="node-name-long",
        minimum=1.25,
        maximum=2.5,
        distance=4.0,
    )

    assert serialize_range(range_) == (
        '     RANGE      level     Z "node-name-long"     4.0'
        "         1.2500         2.5000\n"
    )


def test_serialize_range_quotes_location_over_ten_utf8_bytes() -> None:
    range_ = Range("level", RangeType.LEVEL, location="\u00e9" * 6)

    assert serialize_range(range_).startswith(
        '     RANGE      level     Z "' + "\u00e9" * 6 + '" '
    )


def test_serialize_calendar_time_range() -> None:
    range_ = Range(
        "event",
        RangeType.TIME,
        minimum=datetime(2026, 1, 1, 6, 30),
        maximum=datetime(2026, 1, 1, 18),
    )

    assert serialize_range(range_) == (
        "     RANGE      event     T                0.0 01012026063000 01012026180000\n"
    )


def test_serialize_repeating_time_range() -> None:
    range_ = Range(
        "daily",
        RangeType.TIME_REPEAT,
        minimum=time(6, 30),
        maximum=time(18),
    )

    assert serialize_range(range_) == (
        "     RANGE      daily    TR                0.0 00000000063000 00000000180000\n"
    )


def test_serialize_weekly_repeating_time_range() -> None:
    range_ = Range(
        "weekly",
        RangeType.TIME_REPEAT,
        minimum=WeeklyTime(1, time(6, 30)),
        maximum=WeeklyTime(2, time(18)),
    )

    assert serialize_range(range_) == (
        "     RANGE     weekly    TR                0.0 01000000063000 02000000180000\n"
    )
