from datetime import datetime, time
from inspect import isabstract

from rtc_infoworks_icm.elements.controller import Controller, ControllerType
from rtc_infoworks_icm.elements.logic import Logic, LogicOperator
from rtc_infoworks_icm.elements.range import Range, RangeType
from rtc_infoworks_icm.elements.table import Table, TableRow, TableType
from rtc_infoworks_icm.elements.variable import Variable
from rtc_infoworks_icm.reference import (
    Reference,
    ReferenceKind,
    ReferenceTarget,
    ValueType,
)


def test_reference_target_is_abstract_for_both_contract_properties() -> None:
    assert isabstract(ReferenceTarget)


def test_value_sources_declare_their_value_type() -> None:
    numeric_range = Range("level", RangeType.LEVEL, "node.1")
    datetime_range = Range("date", RangeType.TIME, minimum=datetime(2026, 1, 1))
    repeating_range = Range("daily", RangeType.TIME_REPEAT, minimum=time(6))
    logic = Logic("active", LogicOperator.NOT, Reference(numeric_range))
    table = Table(
        "curve",
        Reference(numeric_range),
        TableType.STEP,
        (TableRow(0, 0.2),),
    )

    assert numeric_range.value_type is ValueType.NUMBER
    assert datetime_range.value_type is ValueType.DATETIME
    assert repeating_range.value_type is ValueType.REPEATING_TIME
    assert logic.value_type is ValueType.NUMBER
    assert table.value_type is ValueType.NUMBER
    assert Variable("total").value_type is ValueType.NUMBER


def test_controller_explicitly_is_not_a_value_source() -> None:
    controller = Controller("pid", ControllerType.INCREMENTAL, 60)

    assert controller.reference_kind is ReferenceKind.CONTROLLER
    assert controller.value_type is None
