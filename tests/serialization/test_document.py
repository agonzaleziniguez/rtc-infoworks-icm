from rtc_infoworks_icm._serialization.document import (
    serialize_header,
    serialize_terminator,
)


def test_serialize_header() -> None:
    assert serialize_header("Example") == (
        "!Version=1,type=RTC,encoding=UTF8       \n         1 Example\n"
    )


def test_serialize_terminator() -> None:
    assert serialize_terminator() == "TERMINATOR\n"
