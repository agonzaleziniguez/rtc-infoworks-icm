"""Serialization of RTC controllers."""

from rtc_infoworks_icm._serialization.fields import (
    serialize_number_field,
    serialize_reference_field,
    serialize_text_field,
)
from rtc_infoworks_icm.elements.controller import Controller

# CENTAUR-type controller fields are not yet supported; this placeholder
# keeps the field positions ICM expects until they are implemented.
_CENTAUR_PLACEHOLDER = "0.000000 0.000000 0.010000 0.010000 0.000000 0.000000"


def serialize_controller(controller: Controller) -> str:
    """Serialize a validated RTC controller."""
    fields = (
        serialize_text_field("CONTROLLER", width=10),
        serialize_text_field(controller.name, width=10),
        serialize_text_field(controller.type.value, width=5),
        serialize_reference_field(controller.sensor, width=10),
        serialize_number_field(controller.measurement_interval, width=5, precision=0),
        serialize_number_field(controller.filter_coefficient, width=8, precision=6),
        serialize_number_field(controller.proportional, width=8, precision=6),
        serialize_number_field(controller.integral, width=8, precision=6),
        serialize_number_field(controller.differential, width=8, precision=6),
        serialize_text_field(None, width=10),
        _CENTAUR_PLACEHOLDER,
    )
    return " ".join(fields) + "\n"
