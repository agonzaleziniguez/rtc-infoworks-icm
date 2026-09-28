from rtc_infoworks_icm import Reference, Variable, VariableOperator
from rtc_infoworks_icm._serialization import serialize_variable


def test_serialize_variable() -> None:
    variable = Variable(
        name="offset",
        operator=VariableOperator.ADD,
        argument_1=Reference("level"),
        argument_2=1.25,
        measurement="level",
    )

    assert serialize_variable(variable) == (
        "  VARIABLE     offset     +          level        1.25000"
        "                  LEVEL\n"
    )
