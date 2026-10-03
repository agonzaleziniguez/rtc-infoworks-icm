from rtc_infoworks_icm._serialization.comment import serialize_comment
from rtc_infoworks_icm.elements.comment import Comment


def test_serialize_comment() -> None:
    assert serialize_comment(Comment("Generated")) == "   COMMENT Generated\n"
