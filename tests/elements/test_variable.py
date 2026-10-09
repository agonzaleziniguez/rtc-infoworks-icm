import pytest

from rtc_infoworks_icm.elements.range import Range, RangeType
from rtc_infoworks_icm.elements.variable import Variable, VariableAssignment, VariableOperator
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


def test_reference_uses_validated_target_name() -> None:
    assert Reference(Range("level", RangeType.LEVEL, "node.1")).name == "level"

    with pytest.raises(RTCValidationError, match="range name cannot be empty"):
        Reference(Range("", RangeType.LEVEL, "node.1"))
    with pytest.raises(RTCValidationError, match="range name cannot be empty"):
        Reference(Range("   ", RangeType.LEVEL, "node.1"))
    with pytest.raises(RTCValidationError, match="cannot exceed 10 characters"):
        Reference(Range("long-reference", RangeType.LEVEL, "node.1"))


def test_variable_preserves_typed_inputs() -> None:
    reference = Reference(Range("level", RangeType.LEVEL, "node.1"))
    variable = VariableAssignment(
        target=Variable("offset"),
        operator=VariableOperator.ADD,
        argument_1=reference,
        argument_2=1.25,
        measurement="level",
    )

    assert variable.operator is VariableOperator.ADD
    assert variable.argument_1 is reference
    assert variable.measurement == "level"


@pytest.mark.parametrize("name", ["", "   ", "long-variable"])
def test_variable_rejects_invalid_name(name: str) -> None:
    with pytest.raises(RTCValidationError):
        VariableAssignment(Variable(name), VariableOperator.ASSIGN, 1.0)


def test_variable_rejects_invalid_measurement() -> None:
    with pytest.raises(RTCValidationError, match="measurement cannot be empty"):
        VariableAssignment(
            Variable("value"), VariableOperator.ASSIGN, 1.0, measurement=""
        )
    with pytest.raises(RTCValidationError, match="measurement cannot be empty"):
        VariableAssignment(
            Variable("value"), VariableOperator.ASSIGN, 1.0, measurement="   "
        )
    with pytest.raises(RTCValidationError, match="cannot exceed 7 characters"):
        VariableAssignment(
            Variable("value"), VariableOperator.ASSIGN, 1.0, measurement="distance"
        )


@pytest.mark.parametrize("argument", [True, float("inf"), float("-inf"), float("nan")])
def test_variable_rejects_invalid_numeric_argument(argument: float) -> None:
    with pytest.raises(RTCValidationError):
        VariableAssignment(Variable("value"), VariableOperator.ASSIGN, argument)


def test_variable_rejects_numeric_argument_that_does_not_fit() -> None:
    with pytest.raises(RTCValidationError, match="does not fit the RTC field"):
        VariableAssignment(Variable("value"), VariableOperator.ASSIGN, 1_000_000_000.0)


def test_assign_variable_rejects_unused_arguments() -> None:
    with pytest.raises(RTCValidationError, match="does not use argument 2"):
        VariableAssignment(Variable("value"), VariableOperator.ASSIGN, 1.0, 2.0)


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
        VariableAssignment(Variable("value"), operator, 1.0)


def test_if_variable_requires_three_arguments() -> None:
    with pytest.raises(RTCValidationError, match="requires argument 3"):
        VariableAssignment(
            Variable("value"),
            VariableOperator.IF,
            Reference(Range("active", RangeType.LEVEL, "node.1")),
            1.0,
        )


def test_timer_variable_allows_optional_reset_and_pause() -> None:
    variable = VariableAssignment(
        Variable("timer"),
        VariableOperator.TIMER,
        Reference(Range("start", RangeType.LEVEL, "node.1")),
        Reference(Range("reset", RangeType.LEVEL, "node.1")),
    )

    assert variable.argument_3 is None
