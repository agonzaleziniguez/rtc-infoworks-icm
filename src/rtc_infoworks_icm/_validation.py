"""Validation shared by multiple RTC models."""

from rtc_infoworks_icm.exceptions import RTCValidationError

_MAX_IDENTIFIER_LENGTH = 10


def validate_identifier(value: str, *, field: str) -> None:
    """Validate an RTC identifier shared by multiple element types."""
    if not value.strip():
        raise RTCValidationError(f"{field} cannot be empty")
    if len(value) > _MAX_IDENTIFIER_LENGTH:
        raise RTCValidationError(
            f"{field} cannot exceed {_MAX_IDENTIFIER_LENGTH} characters"
        )
