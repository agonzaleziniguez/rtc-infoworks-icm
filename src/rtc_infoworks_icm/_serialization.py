"""Internal serialization of InfoWorks ICM RTC document boundaries."""

_VERSION_HEADER = "!Version=1,type=RTC,encoding=UTF8       "
_TERMINATOR = "TERMINATOR"


def serialize_header(name: str) -> str:
    """Serialize the RTC version and document-name lines."""
    return f"{_VERSION_HEADER}\n{1:>10} {name}\n"


def serialize_terminator() -> str:
    """Serialize the fixed RTC document terminator."""
    return f"{_TERMINATOR}\n"
