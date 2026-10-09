from datetime import UTC, datetime, time

import pytest

from rtc_infoworks_icm.elements.range import Range, RangeType, WeeklyTime
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


def test_numeric_range_preserves_values() -> None:
    range_ = Range(
        "level",
        RangeType.LEVEL,
        location="node",
        minimum=1.25,
        maximum=2.5,
        distance=4.0,
    )

    assert range_.location == "node"
    assert range_.minimum == 1.25
    assert range_.maximum == 2.5


@pytest.mark.parametrize("location", [None, "", "   "])
def test_numeric_range_requires_location(location: str | None) -> None:
    with pytest.raises(RTCValidationError, match="location cannot be empty"):
        Range("level", RangeType.LEVEL, location=location)


@pytest.mark.parametrize("location", ['node"name', "first\nsecond"])
def test_numeric_range_rejects_unsafe_location(location: str) -> None:
    with pytest.raises(RTCValidationError, match="quotes or newlines"):
        Range("level", RangeType.LEVEL, location=location)


@pytest.mark.parametrize("value", [True, float("inf"), float("-inf"), float("nan")])
def test_numeric_range_rejects_invalid_bounds(value: float) -> None:
    with pytest.raises(RTCValidationError):
        Range("level", RangeType.LEVEL, location="node", minimum=value)


def test_numeric_range_rejects_reversed_bounds() -> None:
    with pytest.raises(RTCValidationError, match="minimum cannot exceed maximum"):
        Range("level", RangeType.LEVEL, location="node", minimum=2.0, maximum=1.0)


def test_variable_range_rejects_distance() -> None:
    with pytest.raises(RTCValidationError, match="does not use a distance"):
        Range(
            "value",
            RangeType.VARIABLE,
            location=Reference(Range("source", RangeType.LEVEL, "node.1")),
            distance=1.0,
        )


def test_variable_range_rejects_name_only_reference_in_constructor() -> None:
    with pytest.raises(RTCValidationError, match="location must be a Reference"):
        Range("value", RangeType.VARIABLE, location="source")


def test_network_range_location_is_not_limited_to_reference_name_width() -> None:
    range_ = Range("value", RangeType.LEVEL, location="long-network-location")
    assert range_.location == "long-network-location"


def test_calendar_time_range_uses_datetime_bounds() -> None:
    range_ = Range(
        "event",
        RangeType.TIME,
        minimum=datetime(2026, 1, 1, 6),
        maximum=datetime(2026, 1, 1, 18),
    )

    assert range_.minimum == datetime(2026, 1, 1, 6)


def test_repeating_time_range_uses_time_bounds() -> None:
    range_ = Range(
        "daily",
        RangeType.TIME_REPEAT,
        minimum=time(6),
        maximum=time(18),
    )

    assert range_.maximum == time(18)


@pytest.mark.parametrize(
    ("type_", "bound"),
    [
        (RangeType.TIME, time(6)),
        (RangeType.LOCAL_CLOCK_TIME, time(6)),
        (RangeType.TIME_REPEAT, datetime(2026, 1, 1, 6)),
        (RangeType.LOCAL_CLOCK_TIME_REPEAT, datetime(2026, 1, 1, 6)),
    ],
)
def test_time_range_rejects_wrong_bound_type(
    type_: RangeType,
    bound: datetime | time,
) -> None:
    with pytest.raises(RTCValidationError, match="must be a"):
        Range("period", type_, minimum=bound)


def test_time_range_rejects_location_and_distance() -> None:
    with pytest.raises(RTCValidationError, match="does not use a location"):
        Range("event", RangeType.TIME, location="node")
    with pytest.raises(RTCValidationError, match="does not use a distance"):
        Range("event", RangeType.TIME, distance=1.0)


def test_time_range_rejects_timezone() -> None:
    with pytest.raises(RTCValidationError, match="must not include a timezone"):
        Range("event", RangeType.TIME, minimum=datetime(2026, 1, 1, tzinfo=UTC))


def test_range_types_fit_rtc_field() -> None:
    assert all(len(type_.value) <= 5 for type_ in RangeType)


def test_repeating_time_range_accepts_weekly_time_bounds() -> None:
    range_ = Range(
        "weekly",
        RangeType.TIME_REPEAT,
        minimum=WeeklyTime(1, time(6)),
        maximum=WeeklyTime(2, time(6)),
    )

    assert range_.maximum == WeeklyTime(2, time(6))


def test_repeating_time_range_rejects_reversed_weekly_bounds() -> None:
    with pytest.raises(RTCValidationError, match="minimum cannot exceed maximum"):
        Range(
            "weekly",
            RangeType.TIME_REPEAT,
            minimum=WeeklyTime(2, time(6)),
            maximum=WeeklyTime(1, time(6)),
        )


@pytest.mark.parametrize("weekday", [0, 8])
def test_weekly_time_rejects_invalid_weekday(weekday: int) -> None:
    with pytest.raises(RTCValidationError, match="weekday must be between 1 and 7"):
        WeeklyTime(weekday, time(6))


def test_weekly_time_rejects_timezone() -> None:
    with pytest.raises(RTCValidationError, match="must not include a timezone"):
        WeeklyTime(1, time(6, tzinfo=UTC))
