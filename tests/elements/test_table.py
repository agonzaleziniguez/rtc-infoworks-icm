from datetime import UTC, datetime, time

import pytest

from rtc_infoworks_icm import Reference, RTCValidationError, Table, TableRow, TableType


def test_table_preserves_numeric_rows() -> None:
    table = Table(
        "gate",
        Reference("level"),
        TableType.LINEAR,
        (TableRow(0.0, 0.0), TableRow(1.0, 0.5)),
        output_measurement="pos",
    )

    assert table.input_range == Reference("level")
    assert table.rows[1].y == 0.5
    assert table.output_measurement == "pos"


@pytest.mark.parametrize("name", ["", "   ", "long-table-name"])
def test_table_rejects_invalid_name(name: str) -> None:
    with pytest.raises(RTCValidationError):
        Table(name, Reference("level"), TableType.LINEAR, (TableRow(0.0, 0.0),))


def test_table_rejects_invalid_output_measurement() -> None:
    with pytest.raises(RTCValidationError, match="measurement cannot be empty"):
        Table(
            "gate",
            Reference("level"),
            TableType.LINEAR,
            (TableRow(0.0, 0.0),),
            output_measurement="   ",
        )
    with pytest.raises(RTCValidationError, match="cannot exceed 7 characters"):
        Table(
            "gate",
            Reference("level"),
            TableType.LINEAR,
            (TableRow(0.0, 0.0),),
            output_measurement="distance",
        )


def test_table_requires_at_least_one_row() -> None:
    with pytest.raises(RTCValidationError, match="at least one row"):
        Table("gate", Reference("level"), TableType.LINEAR, ())


@pytest.mark.parametrize("x", [True, float("inf"), float("-inf"), float("nan")])
def test_table_row_rejects_invalid_numeric_input(x: float) -> None:
    with pytest.raises(RTCValidationError):
        TableRow(x, 0.0)


@pytest.mark.parametrize("y", [True, float("inf"), float("-inf"), float("nan")])
def test_table_row_rejects_invalid_output(y: float) -> None:
    with pytest.raises(RTCValidationError):
        TableRow(0.0, y)


def test_table_row_rejects_value_that_does_not_fit() -> None:
    with pytest.raises(RTCValidationError, match="does not fit the RTC field"):
        TableRow(1_000_000_000_000.0, 0.0)


def test_table_row_rejects_timezone_aware_datetime() -> None:
    with pytest.raises(RTCValidationError, match="must not include a timezone"):
        TableRow(datetime(2026, 1, 1, tzinfo=UTC), 0.0)


def test_table_rejects_mixed_input_types() -> None:
    with pytest.raises(RTCValidationError, match="single input type"):
        Table(
            "gate",
            Reference("level"),
            TableType.LINEAR,
            (TableRow(0.0, 0.0), TableRow(time(6), 1.0)),
        )


def test_table_rejects_non_ascending_rows() -> None:
    with pytest.raises(RTCValidationError, match="ascending input order"):
        Table(
            "gate",
            Reference("level"),
            TableType.LINEAR,
            (TableRow(1.0, 0.0), TableRow(1.0, 1.0)),
        )


def test_table_accepts_ascending_datetime_rows() -> None:
    table = Table(
        "gate",
        Reference("clock"),
        TableType.STEP,
        (
            TableRow(datetime(2026, 1, 1), 0.0),
            TableRow(datetime(2026, 1, 2), 1.0),
        ),
    )

    assert table.rows[0].x == datetime(2026, 1, 1)
