from rtc_infoworks_icm import Comment
from rtc_infoworks_icm._serialization import (
    serialize_comment,
    serialize_header,
    serialize_terminator,
)


def test_serialize_header() -> None:
    assert serialize_header("Example") == (
        "!Version=1,type=RTC,encoding=UTF8       \n         1 Example\n"
    )


def test_serialize_terminator() -> None:
    assert serialize_terminator() == "TERMINATOR\n"


def test_serialize_comment() -> None:
    assert serialize_comment(Comment("Generated")) == "   COMMENT Generated\n"
