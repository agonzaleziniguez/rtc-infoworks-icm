"""Serialization of RTC comments."""

from rtc_infoworks_icm.elements.comment import Comment


def serialize_comment(comment: Comment) -> str:
    """Serialize a validated RTC comment."""
    return f"{'COMMENT':>10} {comment.text}\n"
