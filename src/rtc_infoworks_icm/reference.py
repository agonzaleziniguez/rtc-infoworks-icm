"""Object references and the shared contract for referenceable RTC elements."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TypeIs

from rtc_infoworks_icm._validation import validate_identifier
from rtc_infoworks_icm.exceptions import RTCValidationError


class ReferenceKind(Enum):
    RANGE = auto()
    TABLE = auto()
    VARIABLE = auto()
    LOGIC = auto()
    CONTROLLER = auto()


class ValueType(Enum):
    NUMBER = auto()
    DATETIME = auto()
    REPEATING_TIME = auto()


@dataclass(frozen=True, slots=True, eq=False)
class ReferenceTarget(ABC):
    """An immutable named identity, never compared by field values."""

    name: str

    def __post_init__(self) -> None:
        validate_identifier(self.name, field="reference target name")

    @property
    @abstractmethod
    def reference_kind(self) -> ReferenceKind:
        """The kind of RTC definition this identity represents."""

    @property
    @abstractmethod
    def value_type(self) -> ValueType | None:
        """The value type this target provides, or None if it is not a value source."""


@dataclass(frozen=True, init=False)
class Reference[T: ReferenceTarget = ReferenceTarget]:
    """An actual target object; the wire-format name is derived from it.

    The read-only target lets model fields retain specific target types.
    """

    _target: T

    def __init__(self, target: T) -> None:
        _validate_target(target)
        object.__setattr__(self, "_target", target)

    @property
    def target(self) -> T:
        return self._target

    @property
    def name(self) -> str:
        return self.target.name


def _validate_target(value: object) -> None:
    if not isinstance(value, ReferenceTarget):
        raise RTCValidationError("reference target must be a referenceable object")


def validate_reference(
    value: object, *, field: str, allowed: tuple[ReferenceKind, ...]
) -> None:
    """Validate the reference and its target kind without document lookup."""
    if not is_reference(value):
        raise RTCValidationError(f"{field} must be a Reference")
    if value.target.reference_kind not in allowed:
        expected = ", ".join(kind.name.title() for kind in allowed)
        raise RTCValidationError(
            f"{field} must reference {expected}, not "
            f"{value.target.reference_kind.name.title()}"
        )


def is_reference(value: object) -> TypeIs[Reference]:
    return isinstance(value, Reference)
