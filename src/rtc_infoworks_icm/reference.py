"""A reference to another RTC element, shared across element types."""

from dataclasses import dataclass

from rtc_infoworks_icm._validation import validate_identifier


@dataclass(frozen=True, slots=True)
class Reference:
    """The name of another RTC element used as an input."""

    name: str

    def __post_init__(self) -> None:
        validate_identifier(self.name, field="reference name")
