import pytest

from rtc_infoworks_icm.elements.controller import Controller, ControllerType
from rtc_infoworks_icm.elements.range import Range, RangeType
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


def test_controller_preserves_values() -> None:
    sensor = Reference(Range("flow", RangeType.FLOW, "node.1"))
    controller = Controller(
        "loop1",
        ControllerType.PID,
        60,
        sensor=sensor,
        filter_coefficient=0.5,
        proportional=-1.0,
        integral=0.1,
        differential=0.0,
    )

    assert controller.name == "loop1"
    assert controller.type is ControllerType.PID
    assert controller.measurement_interval == 60
    assert controller.sensor is sensor
    assert controller.proportional == -1.0


def test_controller_defaults_to_no_sensor_and_zero_coefficients() -> None:
    controller = Controller("inc1", ControllerType.INCREMENTAL, 60)

    assert controller.sensor is None
    assert controller.filter_coefficient == 0.0
    assert controller.proportional == 0.0
    assert controller.integral == 0.0
    assert controller.differential == 0.0


@pytest.mark.parametrize("name", ["", "   ", "long-controller-name"])
def test_controller_rejects_invalid_name(name: str) -> None:
    with pytest.raises(RTCValidationError):
        Controller(name, ControllerType.INCREMENTAL, 60)


@pytest.mark.parametrize("value", [True, 0, -1, 100_000])
def test_controller_rejects_invalid_measurement_interval(value: int) -> None:
    with pytest.raises(RTCValidationError):
        Controller("inc1", ControllerType.INCREMENTAL, value)


def test_controller_rejects_non_integer_measurement_interval() -> None:
    with pytest.raises(RTCValidationError, match="must be an integer"):
        Controller("inc1", ControllerType.INCREMENTAL, 60.5)  # type: ignore[arg-type]


def test_controller_rejects_sensor_on_non_pid_type() -> None:
    with pytest.raises(RTCValidationError, match="sensor is only used with PID"):
        Controller(
            "inc1",
            ControllerType.INCREMENTAL,
            60,
            sensor=Reference(Range("flow", RangeType.LEVEL, "node.1")),
        )


def test_controller_rejects_pid_coefficients_on_non_pid_type() -> None:
    with pytest.raises(
        RTCValidationError, match="proportional coefficient is only used with PID"
    ):
        Controller("inc1", ControllerType.INCREMENTAL, 60, proportional=1.0)


@pytest.mark.parametrize("value", [True, float("inf"), float("-inf"), float("nan")])
def test_controller_rejects_invalid_pid_coefficient(value: float) -> None:
    with pytest.raises(RTCValidationError):
        Controller("pid1", ControllerType.PID, 60, proportional=value)


def test_controller_allows_pid_coefficient_wider_than_the_padded_width() -> None:
    controller = Controller("pid1", ControllerType.PID, 60, proportional=-1.0)
    assert controller.proportional == -1.0
