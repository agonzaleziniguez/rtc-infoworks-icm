from rtc_infoworks_icm._serialization.logic import serialize_logic
from rtc_infoworks_icm.elements.logic import Logic, LogicOperator
from rtc_infoworks_icm.reference import Reference


def test_serialize_binary_logic() -> None:
    logic = Logic(
        "combined",
        LogicOperator.AND,
        Reference("high_level"),
        Reference("high_flow"),
    )

    assert serialize_logic(logic) == (
        "     LOGIC   combined   AND high_level  high_flow                      \n"
    )


def test_serialize_not_logic() -> None:
    logic = Logic("inverted", LogicOperator.NOT, Reference("high_level"))

    assert serialize_logic(logic) == (
        "     LOGIC   inverted   NOT high_level                                 \n"
    )
