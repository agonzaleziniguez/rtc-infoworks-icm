"""Serialization of RTC variables."""

from rtc_infoworks_icm._serialization.fields import (
    serialize_number_field,
    serialize_text_field,
)
from rtc_infoworks_icm.elements.variable import Variable, VariableArgument
from rtc_infoworks_icm.reference import Reference


def serialize_variable(variable: Variable) -> str:
    """Serialize a validated RTC variable."""

    def serialize_argument(argument: VariableArgument | None) -> str:
        if argument is None:
            return serialize_text_field(None, width=14)
        if isinstance(argument, Reference):
            return serialize_text_field(argument.name, width=14)
        return serialize_number_field(argument, width=14, precision=5)

    fields = (
        serialize_text_field("VARIABLE", width=10),
        serialize_text_field(variable.name, width=10),
        serialize_text_field(variable.operator.value, width=5),
        serialize_argument(variable.argument_1),
        serialize_argument(variable.argument_2),
        serialize_argument(variable.argument_3),
        serialize_text_field(
            variable.measurement.upper() if variable.measurement else None,
            width=7,
        ),
    )
    return " ".join(fields) + "\n"
