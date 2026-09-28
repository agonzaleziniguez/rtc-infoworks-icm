"""Serialization fields shared by RTC elements."""


def serialize_text_field(value: str | None, *, width: int) -> str:
    """Serialize validated text as a right-aligned field."""
    return (" " * width) if value is None else value.rjust(width)


def serialize_number_field(
    value: int | float | None,
    *,
    width: int,
    precision: int,
) -> str:
    """Serialize a validated number as a right-aligned field."""
    return " " * width if value is None else f"{value:.{precision}f}".rjust(width)
