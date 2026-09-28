"""Serialization of RTC variables."""

from rtc_infoworks_icm.elements.variable import Reference, Variable, VariableArgument


def serialize_variable(variable: Variable) -> str:
    """Serialize a validated RTC variable."""

    def serialize_argument(argument: VariableArgument | None) -> str:
        if argument is None:
            return " " * 14
        if isinstance(argument, Reference):
            return f"{argument.name:>14}"
        return f"{argument:.5f}".rjust(14)

    fields = (
        f"{'VARIABLE':>10}",
        f"{variable.name:>10}",
        f"{variable.operator.value:>5}",
        serialize_argument(variable.argument_1),
        serialize_argument(variable.argument_2),
        serialize_argument(variable.argument_3),
        f"{(variable.measurement or '').upper():>7}",
    )
    return " ".join(fields) + "\n"
