"""Serialization of RTC regulators."""

from rtc_infoworks_icm._serialization.fields import (
    serialize_location_field,
    serialize_number_field,
)
from rtc_infoworks_icm.elements.regulator import Regulator


def serialize_regulator(regulator: Regulator) -> str:
    """Serialize a validated RTC regulator."""
    # Regulator records omit the keyword and put positive rate before threshold.
    # Numeric fields are cut to eight characters, unlike Controller fields.
    fields = (
        serialize_location_field(regulator.regulator_id),
        serialize_number_field(regulator.initial, width=8, precision=6)[:8],
        serialize_number_field(regulator.positive_rate, width=8, precision=6)[:8],
        serialize_number_field(regulator.threshold, width=8, precision=6)[:8],
        serialize_number_field(regulator.negative_rate, width=8, precision=6)[:8],
        " 1" if regulator.override_other_control else " 0",
    )
    return " ".join(fields) + "\n"
