"""Validation shared by multiple RTC models."""

import math
from enum import StrEnum

from rtc_infoworks_icm.exceptions import RTCValidationError

_MAX_IDENTIFIER_LENGTH = 10


def validate_option(value: object, enum: type[StrEnum], *, field: str) -> None:
    """Require a member of the model's enum without coercion."""
    if not isinstance(value, enum):
        raise RTCValidationError(f"{field} must be a {enum.__name__} member")


def validate_integer(value: object, *, field: str) -> None:
    """Validate a value is an integer but not a boolean."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise RTCValidationError(f"{field} must be an integer")


def validate_text(value: object, *, field: str) -> str:
    """Require text without coercion."""
    if not isinstance(value, str):
        raise RTCValidationError(f"{field} must be text")
    return value


def validate_nonempty_text(value: object, *, field: str) -> str:
    """Require nonblank text without stripping or coercing the stored value."""
    value = validate_text(value, field=field)
    if not value.strip():
        raise RTCValidationError(f"{field} cannot be empty")
    return value


def validate_single_line_text(
    value: object, *, field: str, error_message: str | None = None
) -> None:
    """Require text without carriage returns or newlines."""
    value = validate_text(value, field=field)
    if "\n" in value or "\r" in value:
        raise RTCValidationError(
            error_message
            if error_message is not None
            else f"{field} must be a single line"
        )


def validate_identifier(value: object, *, field: str) -> None:
    """Validate an RTC identifier shared by multiple element types."""
    value = validate_nonempty_text(value, field=field)
    validate_single_line_text(value, field=field)
    if len(value) > _MAX_IDENTIFIER_LENGTH:
        raise RTCValidationError(
            f"{field} cannot exceed {_MAX_IDENTIFIER_LENGTH} characters"
        )


def validate_finite_number(value: object, *, field: str) -> None:
    """Validate a value is a non-bool finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RTCValidationError(f"{field} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise RTCValidationError(f"{field} must be finite")


def validate_formatted_number_width(
    value: int | float,
    *,
    field: str,
    width: int,
    precision: int,
) -> None:
    """Check formatted width after numeric validity has been validated."""
    if len(f"{value:.{precision}f}") > width:
        raise RTCValidationError(f"{field} does not fit the RTC field")
