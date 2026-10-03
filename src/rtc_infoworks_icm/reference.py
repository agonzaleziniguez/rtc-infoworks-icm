"""A reference to another RTC element, shared across element types."""

from dataclasses import dataclass

from rtc_infoworks_icm._validation import validate_identifier
from rtc_infoworks_icm.exceptions import RTCValidationError


@dataclass(frozen=True, slots=True)
class Reference:
    """The name of another RTC element used as an input."""

    name: str

    def __post_init__(self) -> None:
        validate_identifier(self.name, field="reference name")


def validate_reference(value: object, *, field: str) -> None:
    """Require a typed reference without resolving its target."""
    if not isinstance(value, Reference):
        raise RTCValidationError(f"{field} must be a Reference")
