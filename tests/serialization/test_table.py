from datetime import datetime

from rtc_infoworks_icm import Reference, Table, TableRow, TableType
from rtc_infoworks_icm._serialization import serialize_table


def test_serialize_numeric_table() -> None:
    table = Table(
        "gate",
        Reference("level"),
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
        Reference("time"),
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
