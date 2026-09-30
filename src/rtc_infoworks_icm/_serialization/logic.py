"""Serialization of RTC logic."""

from rtc_infoworks_icm._serialization.fields import serialize_text_field
from rtc_infoworks_icm.elements.logic import Logic
from rtc_infoworks_icm.reference import Reference


def serialize_logic(logic: Logic) -> str:
    """Serialize a validated RTC logic definition."""
    conditions = (
        logic.condition_1,
        logic.condition_2,
        logic.condition_3,
        logic.condition_4,
    )
    fields = (
        serialize_text_field("LOGIC", width=10),
        serialize_text_field(logic.name, width=10),
        serialize_text_field(logic.operator.value, width=5),
        *(_serialize_condition(condition) for condition in conditions),
    )
    return " ".join(fields) + "\n"


def _serialize_condition(condition: Reference | None) -> str:
    return serialize_text_field(
        condition.name if condition is not None else None, width=10
    )
