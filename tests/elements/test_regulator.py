from dataclasses import FrozenInstanceError

import pytest

from rtc_infoworks_icm import Regulator, RTCValidationError


def test_regulator_defaults_to_blank_values_and_no_override() -> None:
    regulator = Regulator("pump.1")

    assert regulator.regulator_id == "pump.1"
    assert regulator.initial is None
    assert regulator.threshold is None
    assert regulator.positive_rate is None
    assert regulator.negative_rate is None
    assert regulator.override_other_control is False


def test_regulator_preserves_values() -> None:
    regulator = Regulator(
        "long-network-link.1",
        initial=-1,
        threshold=0.1,
        positive_rate=0.2,
        negative_rate=0.3,
        override_other_control=True,
    )

    assert regulator.regulator_id == "long-network-link.1"
    assert regulator.initial == -1
    assert regulator.threshold == 0.1
    assert regulator.positive_rate == 0.2
    assert regulator.negative_rate == 0.3
    assert regulator.override_other_control is True


@pytest.mark.parametrize("regulator_id", ["", " ", 'pump"1', "pump\n1", "pump\r1"])
def test_regulator_rejects_invalid_id(regulator_id: str) -> None:
    with pytest.raises(RTCValidationError):
        Regulator(regulator_id)


@pytest.mark.parametrize("field", ["initial", "threshold", "positive", "negative"])
@pytest.mark.parametrize("value", [True, float("inf"), float("-inf"), float("nan")])
def test_regulator_rejects_invalid_numeric_values(field: str, value: float) -> None:
    with pytest.raises(RTCValidationError):
        Regulator(
            "pump.1",
            initial=value if field == "initial" else None,
            threshold=value if field == "threshold" else None,
            positive_rate=value if field == "positive" else None,
            negative_rate=value if field == "negative" else None,
        )


def test_regulator_accepts_values_truncated_during_serialization() -> None:
    regulator = Regulator("pump.1", initial=-1, threshold=123.456789)

    assert regulator.initial == -1
    assert regulator.threshold == 123.456789


def test_regulator_rejects_non_boolean_override() -> None:
    with pytest.raises(RTCValidationError, match="must be a boolean"):
        Regulator("pump.1", override_other_control=1)  # type: ignore[arg-type]


def test_regulator_is_immutable() -> None:
    regulator = Regulator("pump.1")

    with pytest.raises(FrozenInstanceError):
        regulator.initial = 1  # type: ignore[misc]
