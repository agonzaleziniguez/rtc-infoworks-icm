import pytest

from rtc_infoworks_icm import RTCValidationError
from rtc_infoworks_icm._validation import (
    validate_finite_number,
    validate_formatted_number_width,
)


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
