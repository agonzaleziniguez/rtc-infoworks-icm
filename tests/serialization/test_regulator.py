import pytest

from rtc_infoworks_icm import Regulator
from rtc_infoworks_icm._serialization import serialize_regulator


def test_serialize_regulator_defaults() -> None:
    assert serialize_regulator(Regulator("pump.1")) == (
        "    pump.1" + " " * 37 + " 0\n"
    )


def test_serialize_regulator_field_order_and_override() -> None:
    regulator = Regulator(
        "gate.1",
        initial=1,
        threshold=0.2,
        positive_rate=0.3,
        negative_rate=0.4,
        override_other_control=True,
    )

    assert serialize_regulator(regulator) == (
        "    gate.1 1.000000 0.300000 0.200000 0.400000  1\n"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-1, "-1.00000"),
        (12.345678, "12.34567"),
        (123_456_789, "12345678"),
        (0.1234567, "0.123457"),
        (0, "0.000000"),
        (-0.0, "-0.00000"),
    ],
)
def test_serialize_regulator_numeric_truncation(value: float, expected: str) -> None:
    regulator = Regulator(
        "pump.1",
        initial=value,
        threshold=value,
        positive_rate=value,
        negative_rate=value,
    )

    assert serialize_regulator(regulator) == (
        f"    pump.1 {expected} {expected} {expected} {expected}  0\n"
    )


@pytest.mark.parametrize(
    ("regulator_id", "expected"),
    [
        ("1234567890", "1234567890"),
        ("12345678901", '"12345678901"'),
        ("long network link.1", '"long network link.1"'),
        ("\u00e9" * 5, " " * 5 + "\u00e9" * 5),
        ("\u00e9" * 6, '"' + "\u00e9" * 6 + '"'),
    ],
)
def test_serialize_regulator_network_id(regulator_id: str, expected: str) -> None:
    assert serialize_regulator(Regulator(regulator_id)) == (
        expected + " " * 37 + " 0\n"
    )


def test_serialize_regulator_keeps_unspecified_fields_blank() -> None:
    assert serialize_regulator(Regulator("pump.1", threshold=0)) == (
        "    pump.1" + " " * 19 + "0.000000" + " " * 10 + " 0\n"
    )
