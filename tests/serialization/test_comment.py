from rtc_infoworks_icm import Comment
from rtc_infoworks_icm._serialization import serialize_comment


def test_serialize_comment() -> None:
    assert serialize_comment(Comment("Generated")) == "   COMMENT Generated\n"
