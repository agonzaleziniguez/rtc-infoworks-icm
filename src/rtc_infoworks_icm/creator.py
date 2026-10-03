"""Fluent creation and writing of RTC files."""

from collections.abc import Sequence
from datetime import datetime, time
from os import PathLike
from pathlib import Path
from typing import Self, cast

from rtc_infoworks_icm._document import RTCElement, validate_document, validate_document_name
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
from rtc_infoworks_icm.elements.variable import Variable, VariableOperator
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


class RTCCreator:
    """Collect RTC records in order, finish with end(), and write a UTF-8 file.

    Definitions before the first regulator are global. Definitions after it
    belong to that regulator until the next regulator declaration. References
    resolve to earlier local definitions first, then global definitions.
    Repeated variable assignments are allowed within a section.
    Other same-scope duplicate names, cross-type name collisions, and repeated
    regulator IDs are rejected. Variables may read their own initial zero value
    in their first assignment; other references must already be declared.

    Supply option enums, element references as names, table rows
    as input/output pairs, and weekly times as (weekday, time) pairs. Invalid
    inputs raise RTCValidationError. String option codes are not accepted;
    element models remain internal.

    Model constructors validate field types and element-specific rules.
    This creator checks pair shapes before construction and validates
    document relationships before writing.
    """

    def __init__(self, name: str) -> None:
        validate_document_name(name)
        self._name = name
        self._elements: list[RTCElement] = []
        self._ended = False

    def comment(self, text: str) -> Self:
        self._require_open()
        self._elements.append(Comment(text))
        return self

    def variable(
        self,
        name: str,
        operator: VariableOperator,
        argument_1: int | float | str,
        argument_2: int | float | str | None = None,
        argument_3: int | float | str | None = None,
        measurement: str | None = None,
    ) -> Self:
        """Add a variable using a VariableOperator member.

        Numeric arguments are constants; strings are element names, including
        strings that look like numbers.
        """
        self._require_open()
        self._elements.append(
            Variable(
                name,
                operator,
                Reference(argument_1) if isinstance(argument_1, str) else argument_1,
                Reference(argument_2) if isinstance(argument_2, str) else argument_2,
                Reference(argument_3) if isinstance(argument_3, str) else argument_3,
                measurement,
            )
        )
        return self

    def range_(
        self,
        name: str,
        type: RangeType,
        location: str | None = None,
        minimum: int | float | datetime | time | tuple[int, time] | None = None,
        maximum: int | float | datetime | time | tuple[int, time] | None = None,
        distance: int | float = 0.0,
    ) -> Self:
        """Add a range using a RangeType member.

        T/LCT bounds use datetime, TR/LCTR bounds use time for daily repeats
        or (weekday, time) for weekly repeats (1=Monday through 7=Sunday).
        Other range codes use numeric bounds.
        """
        self._require_open()
        if isinstance(minimum, tuple):
            _validate_weekly_time_pair(minimum, field="range minimum")
        if isinstance(maximum, tuple):
            _validate_weekly_time_pair(maximum, field="range maximum")
        self._elements.append(
            Range(
                name,
                type,
                location,
                WeeklyTime(*minimum) if isinstance(minimum, tuple) else minimum,
                WeeklyTime(*maximum) if isinstance(maximum, tuple) else maximum,
                distance,
            )
        )
        return self

    def table(
        self,
        name: str,
        input_range: str,
        type: TableType,
        rows: Sequence[
            tuple[int | float | datetime | time | tuple[int, time], int | float]
        ],
        output_measurement: str | None = None,
    ) -> Self:
        """Add a table using a TableType member and (input, output) tuples.

        Inputs use the same numeric/date/time forms as range bounds. Outputs
        are numbers. input_range is the name of a declared input definition.
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
        self._elements.append(
            Table(
                name,
                input_reference,
                type,
                tuple(table_rows),
                output_measurement,
            )
        )
        return self

    def logic(
        self,
        name: str,
        operator: LogicOperator,
        condition_1: str,
        condition_2: str | None = None,
        condition_3: str | None = None,
        condition_4: str | None = None,
    ) -> Self:
        """Add logic using a LogicOperator member and condition names."""
        self._require_open()
        self._elements.append(
            Logic(
                name,
                operator,
                Reference(condition_1),
                Reference(condition_2) if condition_2 is not None else None,
                Reference(condition_3) if condition_3 is not None else None,
                Reference(condition_4) if condition_4 is not None else None,
            )
        )
        return self

    def controller(
        self,
        name: str,
        type: ControllerType,
        measurement_interval: int,
        sensor: str | None = None,
        filter_coefficient: int | float = 0.0,
        proportional: int | float = 0.0,
        integral: int | float = 0.0,
        differential: int | float = 0.0,
    ) -> Self:
        """Add a controller using a ControllerType member.

        sensor is the name of a measurement range.
        """
        self._require_open()
        self._elements.append(
            Controller(
                name,
                type,
                measurement_interval,
                Reference(sensor) if sensor is not None else None,
                filter_coefficient,
                proportional,
                integral,
                differential,
            )
        )
        return self

    def regulator(
        self,
        regulator_id: str,
        initial: int | float | None = None,
        threshold: int | float | None = None,
        positive_rate: int | float | None = None,
        negative_rate: int | float | None = None,
        override_other_control: bool = False,
    ) -> Self:
        self._require_open()
        self._elements.append(
            Regulator(
                regulator_id,
                initial,
                threshold,
                positive_rate,
                negative_rate,
                override_other_control,
            )
        )
        return self

    def rule(
        self,
        type: RuleType,
        condition: str | None = None,
        controller: str | None = None,
        fixed_value: int | float = 0.0,
        variable_value: str | None = None,
    ) -> Self:
        """Add a rule using a RuleType member and optional element names."""
        self._require_open()
        self._elements.append(
            Rule(
                type,
                Reference(condition) if condition is not None else None,
                Reference(controller) if controller is not None else None,
                fixed_value,
                Reference(variable_value) if variable_value is not None else None,
            )
        )
        return self

    def end(self) -> Self:
        """Finish the document; no more records or terminators may be added."""
        self._require_open()
        self._ended = True
        return self

    def write(self, path: str | PathLike[str]) -> None:
        """Validate and write UTF-8 text with LF line endings.

        Validation finishes before the destination is opened. Existing files
        are overwritten on success. Filesystem errors propagate to the caller.
        A finished document may be written to multiple destinations.
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


def _serialize_element(element: RTCElement) -> str:
    if isinstance(element, Comment):
        return serialize_comment(element)
    if isinstance(element, Variable):
        return serialize_variable(element)
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
