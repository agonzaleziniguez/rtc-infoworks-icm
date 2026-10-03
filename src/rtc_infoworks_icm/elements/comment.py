"""RTC comment model."""

from dataclasses import dataclass

from rtc_infoworks_icm._validation import validate_nonempty_text, validate_single_line_text
from rtc_infoworks_icm.exceptions import RTCValidationError

_MAX_COMMENT_LENGTH = 100  # TODO: Confirm the InfoWorks ICM comment length limit.


@dataclass(frozen=True, slots=True)
class Comment:
    """A single-line note in an RTC document."""

    text: str

    def __post_init__(self) -> None:
        validate_nonempty_text(self.text, field="comment text")
        validate_single_line_text(self.text, field="comment text")
        if len(self.text) > _MAX_COMMENT_LENGTH:
            raise RTCValidationError(
                f"comment text cannot exceed {_MAX_COMMENT_LENGTH} characters"
            )
