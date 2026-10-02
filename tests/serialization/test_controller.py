from rtc_infoworks_icm import Controller, ControllerType, Reference
from rtc_infoworks_icm._serialization import serialize_controller


def test_serialize_incremental_controller_with_no_sensor_or_coefficients() -> None:
    controller = Controller("inc1", ControllerType.INCREMENTAL, 60)

    assert serialize_controller(controller) == (
        "CONTROLLER       inc1   INC               60 0.000000 0.000000"
        " 0.000000 0.000000            0.000000 0.000000 0.010000 0.010000"
        " 0.000000 0.000000\n"
    )


def test_serialize_pid_controller_with_sensor_and_coefficients() -> None:
    controller = Controller(
        "pid1",
        ControllerType.PID,
        30,
        sensor=Reference("flow"),
        filter_coefficient=0.5,
        proportional=-1.0,
        integral=0.1,
        differential=0.05,
    )

    assert serialize_controller(controller) == (
        "CONTROLLER       pid1   PID       flow    30 0.500000 -1.000000"
        " 0.100000 0.050000            0.000000 0.000000 0.010000 0.010000"
        " 0.000000 0.000000\n"
    )
