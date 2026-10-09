"""Object-based creation and writing of RTC files."""

from collections.abc import Sequence
from datetime import datetime, time
from enum import Enum, auto
from os import PathLike
from pathlib import Path
from typing import cast, overload

from rtc_infoworks_icm._document import (
    DocumentState,
    RTCElement,
    validate_document,
    validate_document_name,
)
from rtc_infoworks_icm._serialization.comment import serialize_comment
from rtc_infoworks_icm._serialization.controller import serialize_controller
from rtc_infoworks_icm._serialization.document import serialize_header, serialize_terminator
from rtc_infoworks_icm._serialization.logic import serialize_logic
from rtc_infoworks_icm._serialization.range import serialize_range
from rtc_infoworks_icm._serialization.regulator import serialize_regulator
from rtc_infoworks_icm._serialization.rule import serialize_rule
from rtc_infoworks_icm._serialization.table import serialize_table
from rtc_infoworks_icm._serialization.variable import serialize_variable
from rtc_infoworks_icm.elements.comment import Comment
from rtc_infoworks_icm.elements.controller import Controller, ControllerType
from rtc_infoworks_icm.elements.logic import Logic, LogicOperator
from rtc_infoworks_icm.elements.range import Range, RangeType, WeeklyTime
from rtc_infoworks_icm.elements.regulator import Regulator
from rtc_infoworks_icm.elements.rule import Rule, RuleType
from rtc_infoworks_icm.elements.table import Table, TableRow, TableType
from rtc_infoworks_icm.elements.variable import (
    Variable,
    VariableArgument,
    VariableAssignment,
    VariableOperator,
)
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference, ReferenceTarget

type ValueElement = Range | Table | Variable | Logic
type SetpointElement = Range | Table | Variable
type ConditionElement = Range | Logic
type InputArgument = int | float | ValueElement
type InputBound = int | float | datetime | time | tuple[int, time]


class _Missing(Enum):
    OPERATOR = auto()


class RTCCreator:
    """Create immutable objects, finish with end(), and write a UTF-8 RTC file.

    Referenceable methods return their objects, not this creator. Pass those
    objects as references; names are accepted only for new definitions and
    network locations. Other methods return None.

    Definitions before the first regulator are global. After it they are local
    to the current regulator. References must be earlier, visible objects from
    this creator; a local same-name object hides a global one. Same-scope names
    are unique except for updates to the same Variable identity.

    variable(name) reserves an identity without emitting a line. Its first
    assignment may read itself (initial zero); other records require an earlier
    assignment. Updates are restricted to its creation scope. Unused identities
    emit nothing. Failed operations leave the creator unchanged.
    """

    def __init__(self, name: str) -> None:
        validate_document_name(name)
        self._name = name
        self._elements: list[RTCElement] = []
        self._state = DocumentState()
        self._ended = False

    def _append(self, *elements: RTCElement) -> None:
        state = self._state.adding(elements)
        self._elements.extend(elements)
        self._state = state

    def comment(self, text: str) -> None:
        self._require_open()
        self._append(Comment(text))

    @overload
    def variable(self, name: str) -> Variable: ...

    @overload
    def variable(
        self,
        name: str | Variable,
        operator: VariableOperator,
        argument_1: InputArgument,
        argument_2: InputArgument | None = None,
        argument_3: InputArgument | None = None,
        measurement: str | None = None,
    ) -> Variable: ...

    def variable(
        self,
        name: str | Variable,
        operator: VariableOperator | _Missing = _Missing.OPERATOR,
        argument_1: InputArgument | None = None,
        argument_2: InputArgument | None = None,
        argument_3: InputArgument | None = None,
        measurement: str | None = None,
    ) -> Variable:
        """Create a Variable or record an operation on an existing identity.

        Arithmetic operands are explicit: variable(total, ADD, total, 1).
        Measurement describes this assignment record, not a mutable value on
        the identity. No initialization assignment is generated automatically.
        """
        self._require_open()
        creating = isinstance(name, str)
        target = Variable(name) if creating else name
        _validate_variable_target(target)
        if operator is _Missing.OPERATOR:
            if not creating or any(
                value is not None
                for value in (argument_1, argument_2, argument_3, measurement)
            ):
                raise RTCValidationError("variable operation requires an operator")
            self._append(target)
        else:
            assignment = VariableAssignment(
                target,
                operator,
                _variable_argument(argument_1),
                _variable_argument(argument_2) if argument_2 is not None else None,
                _variable_argument(argument_3) if argument_3 is not None else None,
                measurement,
            )
            if creating:
                self._append(target, assignment)
            else:
                self._append(assignment)
        return target

    def range_(
        self,
        name: str,
        type: RangeType,
        location: str | ValueElement | None = None,
        minimum: InputBound | None = None,
        maximum: InputBound | None = None,
        distance: int | float = 0.0,
    ) -> Range:
        """Add a range; VAR locations are objects, network locations are strings.

        T/LCT bounds use datetime. TR/LCTR bounds use time or (weekday, time),
        with weekdays 1=Monday through 7=Sunday.
        """
        self._require_open()
        if isinstance(minimum, tuple):
            _validate_weekly_time_pair(minimum, field="range minimum")
        if isinstance(maximum, tuple):
            _validate_weekly_time_pair(maximum, field="range maximum")
        element = Range(
            name,
            type,
            Reference(location) if isinstance(location, ReferenceTarget) else location,
            WeeklyTime(*minimum) if isinstance(minimum, tuple) else minimum,
            WeeklyTime(*maximum) if isinstance(maximum, tuple) else maximum,
            distance,
        )
        self._append(element)
        return element

    def table(
        self,
        name: str,
        input_range: SetpointElement,
        type: TableType,
        rows: Sequence[tuple[InputBound, int | float]],
        output_measurement: str | None = None,
    ) -> Table:
        """Add a table with a source object and (input, output) row tuples.

        The constructor checks numeric/calendar/repeating-time compatibility.
        Another Table's output is numeric, even when its own input is temporal.
        """
        self._require_open()
        input_reference = Reference(input_range)
        _validate_table_row_collection(rows)
        table_rows: list[TableRow] = []
        for position, row in enumerate(rows, start=1):
            _validate_table_row_pair(row, position)
            x, y = row
            if isinstance(x, tuple):
                _validate_weekly_time_pair(x, field=f"table row {position} input")
                x = WeeklyTime(*x)
            table_rows.append(TableRow(x, y))
        element = Table(
            name, input_reference, type, tuple(table_rows), output_measurement
        )
        self._append(element)
        return element

    def logic(
        self,
        name: str,
        operator: LogicOperator,
        condition_1: ConditionElement,
        condition_2: ConditionElement | None = None,
        condition_3: ConditionElement | None = None,
        condition_4: ConditionElement | None = None,
    ) -> Logic:
        self._require_open()
        element = Logic(
            name,
            operator,
            Reference(condition_1),
            Reference(condition_2) if condition_2 is not None else None,
            Reference(condition_3) if condition_3 is not None else None,
            Reference(condition_4) if condition_4 is not None else None,
        )
        self._append(element)
        return element

    def controller(
        self,
        name: str,
        type: ControllerType,
        measurement_interval: int,
        sensor: Range | None = None,
        filter_coefficient: int | float = 0.0,
        proportional: int | float = 0.0,
        integral: int | float = 0.0,
        differential: int | float = 0.0,
    ) -> Controller:
        self._require_open()
        element = Controller(
            name,
            type,
            measurement_interval,
            Reference(sensor) if sensor is not None else None,
            filter_coefficient,
            proportional,
            integral,
            differential,
        )
        self._append(element)
        return element

    def regulator(
        self,
        regulator_id: str,
        initial: int | float | None = None,
        threshold: int | float | None = None,
        positive_rate: int | float | None = None,
        negative_rate: int | float | None = None,
        override_other_control: bool = False,
    ) -> None:
        self._require_open()
        self._append(
            Regulator(
                regulator_id,
                initial,
                threshold,
                positive_rate,
                negative_rate,
                override_other_control,
            )
        )

    def rule(
        self,
        type: RuleType,
        condition: ConditionElement | None = None,
        controller: Controller | None = None,
        fixed_value: int | float = 0.0,
        variable_value: SetpointElement | None = None,
    ) -> None:
        self._require_open()
        self._append(
            Rule(
                type,
                Reference(condition) if condition is not None else None,
                Reference(controller) if controller is not None else None,
                fixed_value,
                Reference(variable_value) if variable_value is not None else None,
            )
        )

    def end(self) -> None:
        """Close editing; complete-document validation still happens in write()."""
        self._require_open()
        self._ended = True

    def write(self, path: str | PathLike[str]) -> None:
        """Validate before opening the destination; overwrite with UTF-8/LF text.

        A finished document can be written repeatedly. Filesystem errors
        propagate to the caller.
        """
        if not self._ended:
            raise RTCValidationError(
                "document must be finished with end() before write()"
            )
        validate_document(self._name, self._elements)
        text = serialize_header(self._name)
        text += "".join(_serialize_element(element) for element in self._elements)
        text += serialize_terminator()
        Path(path).write_text(text, encoding="utf-8", newline="\n")

    def _require_open(self) -> None:
        if self._ended:
            raise RTCValidationError("document has already ended")


def _validate_variable_target(value: object) -> None:
    if not isinstance(value, Variable):
        raise RTCValidationError("variable target must be a name or Variable object")


def _variable_argument(value: InputArgument | None) -> VariableArgument:
    if isinstance(value, ReferenceTarget):
        return Reference(value)
    if value is None:
        raise RTCValidationError("variable argument 1 must be a number or reference")
    return value


def _serialize_element(element: RTCElement) -> str:
    if isinstance(element, Variable):
        return ""
    if isinstance(element, VariableAssignment):
        return serialize_variable(element)
    if isinstance(element, Comment):
        return serialize_comment(element)
    if isinstance(element, Range):
        return serialize_range(element)
    if isinstance(element, Table):
        return serialize_table(element)
    if isinstance(element, Logic):
        return serialize_logic(element)
    if isinstance(element, Controller):
        return serialize_controller(element)
    if isinstance(element, Regulator):
        return serialize_regulator(element)
    return serialize_rule(element)


def _validate_table_row_collection(rows: object) -> None:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise RTCValidationError("table rows must be a sequence of input/output pairs")


def _validate_table_row_pair(row: object, position: int) -> None:
    if not isinstance(row, tuple) or len(cast(tuple[object, ...], row)) != 2:
        raise RTCValidationError(f"table row {position} must be an input/output pair")


def _validate_weekly_time_pair(value: tuple[object, ...], *, field: str) -> None:
    if len(value) != 2:
        raise RTCValidationError(f"{field} must be a (weekday, time) pair")
