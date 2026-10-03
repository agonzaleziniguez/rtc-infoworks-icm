"""RTC regulator model."""

from dataclasses import dataclass

from rtc_infoworks_icm._validation import validate_finite_number, validate_text
from rtc_infoworks_icm.exceptions import RTCValidationError


@dataclass(frozen=True, slots=True)
class Regulator:
    """Open a network regulator's section; following rules belong to it.

    regulator_id identifies a network link, not an RTC definition. IDs over
    ten UTF-8 bytes are quoted when serialized.

    Optional numeric values left as None produce blank fields. Supplied values
    are formatted with six decimal places, then truncated to eight characters:
    -1 becomes -1.00000 and 12.345678 becomes 12.34567. This can change the
    serialized value without changing the value stored in this model.

    override_other_control defaults to False. Each section needs at least
    one rule, which must be checked when assembling the document.
    """

    regulator_id: str
    initial: int | float | None = None
    threshold: int | float | None = None
    positive_rate: int | float | None = None
    negative_rate: int | float | None = None
    override_other_control: bool = False

    def __post_init__(self) -> None:
        validate_text(self.regulator_id, field="regulator ID")
        if not self.regulator_id.strip():
            raise RTCValidationError("regulator ID cannot be empty")
        if any(character in self.regulator_id for character in ('"', "\r", "\n")):
            raise RTCValidationError(
                "regulator ID cannot contain double quotes or line breaks"
            )
        if type(self.override_other_control) is not bool:
            raise RTCValidationError(
                "regulator override other control must be a boolean"
            )

        for label, value in (
            ("initial", self.initial),
            ("threshold", self.threshold),
            ("positive rate", self.positive_rate),
            ("negative rate", self.negative_rate),
        ):
            if value is not None:
                validate_finite_number(value, field=f"regulator {label}")
