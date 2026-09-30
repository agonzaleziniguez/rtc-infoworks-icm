"""Serialization of RTC rules."""

from rtc_infoworks_icm._serialization.fields import (
    serialize_number_field,
    serialize_reference_field,
    serialize_text_field,
)
from rtc_infoworks_icm.elements.rule import Rule

_FIXED_VALUE_PRECISION = 4
# RTC represents a zero fixed value with 6 decimal places instead of 4;
# see rtc_infoworks_icm.elements.rule for the matching validation.
_ZERO_FIXED_VALUE_PRECISION = 6


def serialize_rule(rule: Rule) -> str:
    """Serialize a validated RTC rule."""
    precision = (
        _ZERO_FIXED_VALUE_PRECISION
        if rule.fixed_value == 0.0
        else _FIXED_VALUE_PRECISION
    )
    fields = (
        serialize_text_field("RULE", width=10),
        serialize_reference_field(rule.condition, width=10),
        serialize_text_field(rule.type.value, width=5),
        serialize_number_field(rule.fixed_value, width=8, precision=precision),
        serialize_reference_field(rule.controller, width=10),
        serialize_reference_field(rule.variable_value, width=10),
    )
    return " ".join(fields) + "\n"
