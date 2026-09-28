"""RTC comment model."""

from dataclasses import dataclass

from rtc_infoworks_icm.exceptions import RTCValidationError

_MAX_COMMENT_LENGTH = 100  # TODO: Confirm the InfoWorks ICM comment length limit.


@dataclass(frozen=True, slots=True)
class Comment:
    """A single-line note in an RTC document."""

    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise RTCValidationError("comment text cannot be empty")
        if "\n" in self.text or "\r" in self.text:
            raise RTCValidationError("comment text must be a single line")
        if len(self.text) > _MAX_COMMENT_LENGTH:
            raise RTCValidationError(
                f"comment text cannot exceed {_MAX_COMMENT_LENGTH} characters"
            )
