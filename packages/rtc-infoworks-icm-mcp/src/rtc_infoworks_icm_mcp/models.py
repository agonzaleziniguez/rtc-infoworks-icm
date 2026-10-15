"""Strict wire contracts for ordered library operations and edits."""

from collections.abc import Callable
from datetime import datetime, time
from enum import StrEnum
from typing import Annotated, Literal, TypeIs

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    ValidationError,
    field_validator,
)

from rtc_infoworks_icm import (
    ControllerType,
    LogicOperator,
    RangeType,
    RuleType,
    TableType,
    VariableOperator,
)

type Number = StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)]
type Identifier = Annotated[
    str, Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
]


def _is_json_array(value: object) -> TypeIs[list[object]]:
    return isinstance(value, list)


def _freeze_array(value: object) -> object:
    # The SDK validates decoded JSON; arrays arrive as lists, not tuples.
    return tuple(value) if _is_json_array(value) else value


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ReferenceInput(ContractModel):
    ref: Identifier


class NumericInput(ContractModel):
    kind: Literal["number"]
    value: Number


class CalendarInput(ContractModel):
    kind: Literal["datetime"]
    value: Annotated[
        str,
        Field(pattern=r"^[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$"),
    ]

    @field_validator("value")
    @classmethod
    def validate_calendar(cls, value: str) -> str:
        if datetime.fromisoformat(value).isoformat(timespec="seconds") != value:
            raise ValueError("datetime must use a canonical wall-clock value")
        return value

    def to_python(self) -> datetime:
        return datetime.fromisoformat(self.value)


class ClockInput(ContractModel):
    value: Annotated[str, Field(pattern=r"^[0-9]{2}:[0-9]{2}:[0-9]{2}$")]

    @field_validator("value")
    @classmethod
    def validate_time(cls, value: str) -> str:
        if time.fromisoformat(value).isoformat(timespec="seconds") != value:
            raise ValueError(
                "time must use a canonical value from 00:00:00 to 23:59:59"
            )
        return value

    def to_python(self) -> time:
        return time.fromisoformat(self.value)


class TimeInput(ClockInput):
    kind: Literal["time"]


class WeeklyTimeInput(ClockInput):
    kind: Literal["weekly_time"]
    weekday: Annotated[StrictInt, Field(ge=1, le=7)]


type BoundInput = Annotated[
    NumericInput | CalendarInput | TimeInput | WeeklyTimeInput,
    Field(discriminator="kind"),
]
type ArgumentInput = Number | ReferenceInput


class TableRowInput(ContractModel):
    input: BoundInput
    output: Number


class OperationModel(ContractModel):
    id: Identifier


def _enum_decoder(enum: type[StrEnum]) -> Callable[[object], object]:
    def decode(value: object) -> object:
        if type(value) is str:
            try:
                return enum(value)
            except ValueError as error:
                raise ValueError(
                    f"expected a {enum.__name__} serialized value"
                ) from error
        return value

    return decode


class AddComment(OperationModel):
    method: Literal["comment"]
    text: str


class AddRange(OperationModel):
    method: Literal["range_"]
    name: str
    type: Annotated[RangeType, BeforeValidator(_enum_decoder(RangeType))]
    location: str | ReferenceInput | None = None
    minimum: BoundInput | None = None
    maximum: BoundInput | None = None
    distance: Number = 0.0


class AddTable(OperationModel):
    method: Literal["table"]
    name: str
    input_range: ReferenceInput
    type: Annotated[TableType, BeforeValidator(_enum_decoder(TableType))]
    rows: Annotated[tuple[TableRowInput, ...], BeforeValidator(_freeze_array)]
    output_measurement: str | None = None


class DeclareVariable(OperationModel):
    method: Literal["declare_variable"]
    name: str


class AssignVariable(OperationModel):
    method: Literal["assign_variable"]
    target: ReferenceInput
    operator: Annotated[
        VariableOperator, BeforeValidator(_enum_decoder(VariableOperator))
    ]
    argument_1: ArgumentInput
    argument_2: ArgumentInput | None = None
    argument_3: ArgumentInput | None = None
    measurement: str | None = None


class AddLogic(OperationModel):
    method: Literal["logic"]
    name: str
    operator: Annotated[LogicOperator, BeforeValidator(_enum_decoder(LogicOperator))]
    condition_1: ReferenceInput
    condition_2: ReferenceInput | None = None
    condition_3: ReferenceInput | None = None
    condition_4: ReferenceInput | None = None


class AddController(OperationModel):
    method: Literal["controller"]
    name: str
    type: Annotated[ControllerType, BeforeValidator(_enum_decoder(ControllerType))]
    measurement_interval: StrictInt
    sensor: ReferenceInput | None = None
    filter_coefficient: Number = 0.0
    proportional: Number = 0.0
    integral: Number = 0.0
    differential: Number = 0.0


class BeginRegulator(OperationModel):
    method: Literal["regulator"]
    regulator_id: str
    initial: Number | None = None
    threshold: Number | None = None
    positive_rate: Number | None = None
    negative_rate: Number | None = None
    override_other_control: bool = False


class AddRule(OperationModel):
    method: Literal["rule"]
    type: Annotated[RuleType, BeforeValidator(_enum_decoder(RuleType))]
    condition: ReferenceInput | None = None
    controller: ReferenceInput | None = None
    fixed_value: Number = 0.0
    variable_value: ReferenceInput | None = None


type Operation = Annotated[
    AddComment
    | AddRange
    | AddTable
    | DeclareVariable
    | AssignVariable
    | AddLogic
    | AddController
    | BeginRegulator
    | AddRule,
    Field(discriminator="method"),
]


class DefinitionInput(ContractModel):
    name: str
    operations: Annotated[tuple[Operation, ...], BeforeValidator(_freeze_array)]


class InsertEdit(ContractModel):
    action: Literal["insert"]
    operation: Operation
    before: Identifier | None = None


class ReplaceEdit(ContractModel):
    action: Literal["replace"]
    target: Identifier
    operation: Operation


class RemoveEdit(ContractModel):
    action: Literal["remove"]
    target: Identifier


type Edit = Annotated[
    InsertEdit | ReplaceEdit | RemoveEdit, Field(discriminator="action")
]


class EditRequest(ContractModel):
    definition_id: Identifier
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    edits: Annotated[
        tuple[Edit, ...], Field(min_length=1), BeforeValidator(_freeze_array)
    ]


class Diagnostic(ContractModel):
    code: Literal[
        "invalid_request",
        "duplicate_operation_id",
        "unknown_reference",
        "wrong_reference_kind",
        "invalid_document",
        "incomplete_document",
    ]
    message: str
    operation_id: str | None = None
    operation_index: StrictInt | None = None
    field: str | None = None


class RequestError(Exception):
    """Malformed input, distinguished from library construction failures."""

    def __init__(self, diagnostics: tuple[Diagnostic, ...]) -> None:
        self.diagnostics = diagnostics
        super().__init__("; ".join(diagnostic.message for diagnostic in diagnostics))


def parse_definition(payload: str | bytes) -> DefinitionInput:
    """Decode strict JSON and report contextual errors without raw input objects."""
    return _parse(DefinitionInput, payload)


def parse_edits(payload: str | bytes) -> EditRequest:
    """Decode an edit request; applying edits belongs to the definition service."""
    return _parse(EditRequest, payload)


def _parse[T: ContractModel](model: type[T], payload: str | bytes) -> T:
    try:
        return model.model_validate_json(payload)
    except ValidationError as error:
        diagnostics: list[Diagnostic] = []
        for detail in error.errors(include_url=False, include_input=False):
            location = detail["loc"]
            index = (
                location[1]
                if len(location) > 1
                and location[0] == "operations"
                and isinstance(location[1], int)
                else None
            )
            diagnostics.append(
                Diagnostic(
                    code="invalid_request",
                    message=detail["msg"],
                    operation_index=index,
                    field=".".join(str(part) for part in location) or None,
                )
            )
        raise RequestError(tuple(diagnostics)) from error
