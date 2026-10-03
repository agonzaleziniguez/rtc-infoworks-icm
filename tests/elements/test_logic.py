import pytest

from rtc_infoworks_icm.elements.logic import Logic, LogicOperator
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


def test_logic_preserves_conditions() -> None:
    logic = Logic(
        "combined",
        LogicOperator.AND,
        Reference("high_level"),
        Reference("high_flow"),
    )

    assert logic.operator is LogicOperator.AND
    assert logic.condition_1 == Reference("high_level")
    assert logic.condition_2 == Reference("high_flow")
    assert logic.condition_3 is None


@pytest.mark.parametrize("name", ["", "   ", "long-logic-name"])
def test_logic_rejects_invalid_name(name: str) -> None:
    with pytest.raises(RTCValidationError):
        Logic(name, LogicOperator.AND, Reference("a"), Reference("b"))


def test_not_logic_needs_only_the_required_condition() -> None:
    logic = Logic("inverted", LogicOperator.NOT, Reference("high_level"))
    assert logic.condition_2 is None


@pytest.mark.parametrize(
    "operator",
    [LogicOperator.AND, LogicOperator.OR, LogicOperator.NAND, LogicOperator.NOR],
)
def test_binary_logic_requires_two_conditions(operator: LogicOperator) -> None:
    with pytest.raises(RTCValidationError, match="requires at least 2 condition"):
        Logic("combined", operator, Reference("a"))


def test_logic_rejects_gap_between_conditions() -> None:
    with pytest.raises(RTCValidationError, match="cannot skip a position"):
        Logic(
            "combined",
            LogicOperator.AND,
            Reference("a"),
            None,
            Reference("c"),
        )
