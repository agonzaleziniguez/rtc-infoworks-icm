from datetime import datetime, time

from rtc_infoworks_icm._serialization.table import serialize_table
from rtc_infoworks_icm.elements.range import Range, RangeType, WeeklyTime
from rtc_infoworks_icm.elements.table import Table, TableRow, TableType
from rtc_infoworks_icm.reference import Reference


def test_serialize_numeric_table() -> None:
    table = Table(
        "gate",
        Reference(Range("level", RangeType.LEVEL, "node.1")),
        TableType.LINEAR,
        (TableRow(0.0, 0.0), TableRow(1.0, 0.5)),
        output_measurement="pos",
    )

    assert serialize_table(table) == (
        "     TABLE       gate      level     POS LINEAR\n"
        "TABLEENTRY                                0.000          0.000\n"
        "TABLEENTRY                                1.000          0.500\n"
    )


def test_serialize_datetime_table() -> None:
    table = Table(
        "clock",
        Reference(Range("time", RangeType.TIME)),
        TableType.STEP,
        (
            TableRow(datetime(2026, 1, 1, 6, 30), 0.2),
            TableRow(datetime(2026, 1, 2, 12), 0.8),
        ),
    )

    assert serialize_table(table) == (
        "     TABLE      clock       time           STEP\n"
        "TABLEENTRY                       01012026063000          0.200\n"
        "TABLEENTRY                       02012026120000          0.800\n"
    )


def test_serialize_weekly_time_table() -> None:
    table = Table(
        "weekly",
        Reference(Range("wk", RangeType.TIME_REPEAT)),
        TableType.STEP,
        (
            TableRow(WeeklyTime(1, time(6)), 0.2),
            TableRow(WeeklyTime(2, time(6)), 0.8),
        ),
    )

    assert serialize_table(table) == (
        "     TABLE     weekly         wk           STEP\n"
        "TABLEENTRY                       01000000060000          0.200\n"
        "TABLEENTRY                       02000000060000          0.800\n"
    )
