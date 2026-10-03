import pytest

from rtc_infoworks_icm._validation import (
    validate_finite_number,
    validate_formatted_number_width,
    validate_identifier,
    validate_nonempty_text,
    validate_single_line_text,
)
from rtc_infoworks_icm.exceptions import RTCValidationError


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), float("-inf")])
def test_numeric_validity_rejects_invalid_numbers(value: float) -> None:
    with pytest.raises(RTCValidationError):
        validate_finite_number(value, field="test value")


def test_numeric_validity_does_not_restrict_formatted_width() -> None:
    validate_finite_number(-1, field="test value")


@pytest.mark.parametrize("value", [1, 0.1234567])
def test_formatted_width_accepts_exact_width(value: float) -> None:
    validate_formatted_number_width(value, field="test value", width=8, precision=6)


@pytest.mark.parametrize("value", [-1, 9.9999999])
def test_formatted_width_counts_sign_and_rounding(value: float) -> None:
    with pytest.raises(RTCValidationError, match="does not fit the RTC field"):
        validate_formatted_number_width(value, field="test value", width=8, precision=6)


def test_formatted_width_uses_requested_precision() -> None:
    validate_formatted_number_width(-1, field="test value", width=8, precision=4)


@pytest.mark.parametrize("value", [None, True, 1, [], b"text"])
def test_text_validators_reject_nontext(value: object) -> None:
    with pytest.raises(RTCValidationError, match="^test value must be text$"):
        validate_nonempty_text(value, field="test value")
    with pytest.raises(RTCValidationError, match="^test value must be text$"):
        validate_single_line_text(value, field="test value")


@pytest.mark.parametrize("value", ["", " ", "\t", "\r\n"])
def test_nonempty_text_rejects_blank_values(value: str) -> None:
    with pytest.raises(RTCValidationError, match="^test value cannot be empty$"):
        validate_nonempty_text(value, field="test value")


def test_nonempty_text_preserves_whitespace_and_allows_multiple_lines() -> None:
    value = " first\nsecond "
    assert validate_nonempty_text(value, field="test value") == value


@pytest.mark.parametrize("value", ["first\nsecond", "first\rsecond", "first\r\nsecond"])
def test_single_line_text_rejects_line_breaks(value: str) -> None:
    with pytest.raises(RTCValidationError, match="^test value must be a single line$"):
        validate_single_line_text(value, field="test value")


@pytest.mark.parametrize("value", ["", " ", " padded ", 'quoted"text', "a\tb"])
def test_single_line_text_does_not_add_other_restrictions(value: str) -> None:
    validate_single_line_text(value, field="test value")


def test_single_line_text_preserves_custom_error_message() -> None:
    with pytest.raises(RTCValidationError, match="^existing field message$"):
        validate_single_line_text(
            "first\nsecond", field="test value", error_message="existing field message"
        )


def test_identifier_keeps_existing_rules() -> None:
    validate_identifier("a\nb", field="test value")
    with pytest.raises(RTCValidationError, match="cannot exceed 10 characters"):
        validate_identifier("12345678901", field="test value")
