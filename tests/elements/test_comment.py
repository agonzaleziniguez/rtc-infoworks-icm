from dataclasses import FrozenInstanceError

import pytest

from rtc_infoworks_icm.elements.comment import Comment
from rtc_infoworks_icm.exceptions import RTCValidationError


def test_comment_preserves_valid_text() -> None:
    comment = Comment("Control pump P1")

    assert comment.text == "Control pump P1"


@pytest.mark.parametrize("text", ["", "   ", "\n", "first\nsecond", "first\rsecond"])
def test_comment_rejects_invalid_text(text: str) -> None:
    with pytest.raises(RTCValidationError):
        Comment(text)


def test_comment_accepts_100_characters() -> None:
    assert len(Comment("a" * 100).text) == 100


def test_comment_rejects_more_than_100_characters() -> None:
    with pytest.raises(
        RTCValidationError,
        match="comment text cannot exceed 100 characters",
    ):
        Comment("a" * 101)


def test_comment_is_immutable() -> None:
    comment = Comment("Control pump P1")

    with pytest.raises(FrozenInstanceError):
        setattr(comment, "text", "Changed")
