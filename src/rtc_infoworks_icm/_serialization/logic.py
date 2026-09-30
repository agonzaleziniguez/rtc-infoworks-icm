"""Serialization of RTC logic."""

from rtc_infoworks_icm._serialization.fields import (
    serialize_reference_field,
    serialize_text_field,
)
from rtc_infoworks_icm.elements.logic import Logic


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
        *(serialize_reference_field(condition, width=10) for condition in conditions),
    )
    return " ".join(fields) + "\n"
