import pytest

from rtc_infoworks_icm.elements.variable import Variable, VariableOperator
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


def test_reference_validates_name() -> None:
    assert Reference("level").name == "level"

    with pytest.raises(RTCValidationError, match="reference name cannot be empty"):
        Reference("")
    with pytest.raises(RTCValidationError, match="reference name cannot be empty"):
        Reference("   ")
    with pytest.raises(RTCValidationError, match="cannot exceed 10 characters"):
        Reference("long-reference")


def test_variable_preserves_typed_inputs() -> None:
    variable = Variable(
        name="offset",
        operator=VariableOperator.ADD,
        argument_1=Reference("level"),
        argument_2=1.25,
        measurement="level",
    )

    assert variable.operator is VariableOperator.ADD
    assert variable.argument_1 == Reference("level")
    assert variable.measurement == "level"


@pytest.mark.parametrize("name", ["", "   ", "long-variable"])
def test_variable_rejects_invalid_name(name: str) -> None:
    with pytest.raises(RTCValidationError):
        Variable(name, VariableOperator.ASSIGN, 1.0)


def test_variable_rejects_invalid_measurement() -> None:
    with pytest.raises(RTCValidationError, match="measurement cannot be empty"):
        Variable("value", VariableOperator.ASSIGN, 1.0, measurement="")
    with pytest.raises(RTCValidationError, match="measurement cannot be empty"):
        Variable("value", VariableOperator.ASSIGN, 1.0, measurement="   ")
    with pytest.raises(RTCValidationError, match="cannot exceed 7 characters"):
        Variable("value", VariableOperator.ASSIGN, 1.0, measurement="distance")


@pytest.mark.parametrize("argument", [True, float("inf"), float("-inf"), float("nan")])
def test_variable_rejects_invalid_numeric_argument(argument: float) -> None:
    with pytest.raises(RTCValidationError):
        Variable("value", VariableOperator.ASSIGN, argument)


def test_variable_rejects_numeric_argument_that_does_not_fit() -> None:
    with pytest.raises(RTCValidationError, match="does not fit the RTC field"):
        Variable("value", VariableOperator.ASSIGN, 1_000_000_000.0)


def test_assign_variable_rejects_unused_arguments() -> None:
    with pytest.raises(RTCValidationError, match="does not use argument 2"):
        Variable("value", VariableOperator.ASSIGN, 1.0, 2.0)


@pytest.mark.parametrize(
    "operator",
    [
        VariableOperator.ADD,
        VariableOperator.SUBTRACT,
        VariableOperator.DIVIDE,
        VariableOperator.MULTIPLY,
    ],
)
def test_binary_variable_requires_two_arguments(operator: VariableOperator) -> None:
    with pytest.raises(RTCValidationError, match="requires argument 2"):
        Variable("value", operator, 1.0)


def test_if_variable_requires_three_arguments() -> None:
    with pytest.raises(RTCValidationError, match="requires argument 3"):
        Variable("value", VariableOperator.IF, Reference("active"), 1.0)


def test_timer_variable_allows_optional_reset_and_pause() -> None:
    variable = Variable(
        "timer",
        VariableOperator.TIMER,
        Reference("start"),
        Reference("reset"),
    )

    assert variable.argument_3 is None
