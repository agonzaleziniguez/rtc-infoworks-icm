"""RTC logic model."""

from dataclasses import dataclass
from enum import StrEnum

from rtc_infoworks_icm._validation import validate_identifier, validate_option
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference, validate_reference

_MINIMUM_CONDITIONS = {
    "AND": 2,
    "OR": 2,
    "NOR": 2,
    "NAND": 2,
}


class LogicOperator(StrEnum):
    """Supported operators for combining RTC conditions."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    NOR = "NOR"
    NAND = "NAND"


@dataclass(frozen=True, slots=True)
class Logic:
    """A TRUE/FALSE result combining up to four ranges or other logic."""

    name: str
    operator: LogicOperator
    condition_1: Reference
    condition_2: Reference | None = None
    condition_3: Reference | None = None
    condition_4: Reference | None = None

    def __post_init__(self) -> None:
        validate_option(self.operator, LogicOperator, field="logic operator")
        validate_identifier(self.name, field="logic name")
        validate_reference(self.condition_1, field="logic condition 1")
        for position, condition in enumerate(
            (self.condition_2, self.condition_3, self.condition_4), start=2
        ):
            if condition is not None:
                validate_reference(condition, field=f"logic condition {position}")
        self._validate_conditions_contiguous()
        self._validate_condition_count()

    def _validate_conditions_contiguous(self) -> None:
        conditions = (
            self.condition_1,
            self.condition_2,
            self.condition_3,
            self.condition_4,
        )
        seen_gap = False
        for condition in conditions:
            if condition is None:
                seen_gap = True
            elif seen_gap:
                raise RTCValidationError("logic conditions cannot skip a position")

    def _validate_condition_count(self) -> None:
        minimum = _MINIMUM_CONDITIONS.get(self.operator.value)
        if minimum is None:
            return
        conditions = (
            self.condition_1,
            self.condition_2,
            self.condition_3,
            self.condition_4,
        )
        count = sum(1 for condition in conditions if condition is not None)
        if count < minimum:
            raise RTCValidationError(
                f"{self.operator.value.lower()} logic requires at least "
                f"{minimum} condition(s)"
            )
