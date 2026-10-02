"""Validation shared by multiple RTC models."""

import math

from rtc_infoworks_icm.exceptions import RTCValidationError

_MAX_IDENTIFIER_LENGTH = 10


def validate_integer(value: object, *, field: str) -> None:
    """Validate a value is an integer but not a boolean."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise RTCValidationError(f"{field} must be an integer")


def validate_identifier(value: str, *, field: str) -> None:
    """Validate an RTC identifier shared by multiple element types."""
    if not value.strip():
        raise RTCValidationError(f"{field} cannot be empty")
    if len(value) > _MAX_IDENTIFIER_LENGTH:
        raise RTCValidationError(
            f"{field} cannot exceed {_MAX_IDENTIFIER_LENGTH} characters"
        )


def validate_finite(value: int | float, *, field: str) -> None:
    """Validate a value is a non-bool finite number."""
    if isinstance(value, bool):
        raise RTCValidationError(f"{field} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise RTCValidationError(f"{field} must be finite")


def validate_finite_number(
    value: int | float,
    *,
    field: str,
    width: int,
    precision: int,
) -> None:
    """Validate a value is a non-bool finite number that fits an RTC field."""
    validate_finite(value, field=field)
    if len(f"{value:.{precision}f}") > width:
        raise RTCValidationError(f"{field} does not fit the RTC field")
