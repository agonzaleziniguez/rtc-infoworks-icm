from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import datetime, time
from pathlib import Path
from typing import get_overloads, get_type_hints

import pytest

import rtc_infoworks_icm
from rtc_infoworks_icm import (
    Controller,
    ControllerType,
    Logic,
    LogicOperator,
    Range,
    RangeType,
    RTCCreator,
    RTCValidationError,
    RuleType,
    Table,
    TableType,
    Variable,
    VariableOperator,
)


def _finish(rtc: RTCCreator) -> None:
    rtc.regulator("pump.1")
    rtc.rule(RuleType.POSITION)
    rtc.end()


def test_creator_writes_exact_minimal_document(tmp_path: Path) -> None:
    path = tmp_path / "control.rtc"
    rtc = RTCCreator("Example")
    assert rtc.regulator("pump.1") is None
    assert rtc.rule(RuleType.POSITION) is None
    assert rtc.end() is None
    assert rtc.write(path) is None
    assert path.read_bytes() == (
        b"!Version=1,type=RTC,encoding=UTF8       \n         1 Example\n"
        + b"    pump.1"
        + b" " * 37
        + b" 0\n"
        + b"      RULE              POS 0.000000                      \n"
        + b"TERMINATOR\n"
    )


def test_creator_wires_every_element_and_preserves_order(tmp_path: Path) -> None:
    rtc = RTCCreator("Control")
    assert rtc.comment("Global definitions") is None
    level = rtc.range_("level", RangeType.LEVEL, "node.1", 1, 2, 4)
    value = rtc.variable("value", VariableOperator.ASSIGN, 1)
    lookup = rtc.table("lookup", level, TableType.STEP, [(1, 2)], "FLOW")
    high = rtc.logic("high", LogicOperator.NOT, level)
    pid = rtc.controller("pid", ControllerType.PID, 60, level, 0.5, -1, 0.1, 0.05)
    assert isinstance(level, Range)
    assert isinstance(value, Variable)
    assert isinstance(lookup, Table)
    assert isinstance(high, Logic)
    assert isinstance(pid, Controller)
    assert lookup.input_range.target is level
    assert high.condition_1.target is level
    assert pid.sensor is not None and pid.sensor.target is level
    assert rtc.regulator("pump.1", -1, 0.1, 0.2, 0.3, True) is None
    assert rtc.rule(RuleType.CONTROL, high, pid, 1, lookup) is None
    rtc.end()
    path = tmp_path / "control.rtc"
    rtc.write(str(path))
    assert path.read_bytes() == (
        b"!Version=1,type=RTC,encoding=UTF8       \n         1 Control\n"
        b"   COMMENT Global definitions\n"
        b"     RANGE      level     Z     node.1     4.0"
        b"         1.0000         2.0000\n"
        b"  VARIABLE      value     =        1.00000"
        b"                                      \n"
        b"     TABLE     lookup      level    FLOW   STEP\n"
        b"TABLEENTRY                                1.000          2.000\n"
        b"     LOGIC       high   NOT      level                                 \n"
        b"CONTROLLER        pid   PID      level    60"
        b" 0.500000 -1.000000 0.100000 0.050000           "
        b" 0.000000 0.000000 0.010000 0.010000 0.000000 0.000000\n"
        b"    pump.1 -1.00000 0.200000 0.100000 0.300000  1\n"
        b"      RULE       high  CTRL   1.0000        pid     lookup\n"
        b"TERMINATOR\n"
    )


def test_creator_preserves_exact_scoped_variable_and_temporal_table_output(
    tmp_path: Path,
) -> None:
    rtc = RTCCreator("Scoped")
    total = rtc.variable("total")
    rtc.variable(total, VariableOperator.ADD, total, 1)
    rtc.variable(total, VariableOperator.MULTIPLY, total, 2, measurement="m")
    daily = rtc.range_(
        "daily", RangeType.TIME_REPEAT, minimum=time(6), maximum=time(18)
    )
    daycurve = rtc.table(
        "daycurve", daily, TableType.STEP, [(time(6), 0.2), (time(18), 0.8)]
    )
    week = rtc.range_(
        "week", RangeType.TIME_REPEAT, minimum=(1, time(6)), maximum=(2, time(6))
    )
    wkcurve = rtc.table(
        "wkcurve",
        week,
        TableType.STEP,
        [((1, time(6)), 0.2), ((2, time(6)), 0.8)],
    )
    rtc.regulator("pump.1")
    local = rtc.variable("total")
    rtc.variable(local, VariableOperator.ADD, local, 3)
    rtc.variable(local, VariableOperator.MULTIPLY, local, 4)
    rtc.rule(RuleType.POSITION, variable_value=local)
    rtc.rule(RuleType.POSITION, variable_value=daycurve)
    rtc.regulator("pump.2")
    next_local = rtc.variable("total", VariableOperator.ASSIGN, 5)
    rtc.rule(RuleType.POSITION, variable_value=next_local)
    rtc.rule(RuleType.POSITION, variable_value=wkcurve)
    rtc.end()
    path = tmp_path / "scoped.rtc"
    rtc.write(path)
    assert path.read_bytes() == (
        b"!Version=1,type=RTC,encoding=UTF8       \n         1 Scoped\n"
        b"  VARIABLE      total     +          total        1.00000"
        b"                       \n"
        b"  VARIABLE      total     *          total        2.00000"
        b"                      M\n"
        b"     RANGE      daily    TR                0.0"
        b" 00000000060000 00000000180000\n"
        b"     TABLE   daycurve      daily           STEP\n"
        b"TABLEENTRY                       00000000060000          0.200\n"
        b"TABLEENTRY                       00000000180000          0.800\n"
        b"     RANGE       week    TR                0.0"
        b" 01000000060000 02000000060000\n"
        b"     TABLE    wkcurve       week           STEP\n"
        b"TABLEENTRY                       01000000060000          0.200\n"
        b"TABLEENTRY                       02000000060000          0.800\n"
        b"    pump.1                                      0\n"
        b"  VARIABLE      total     +          total        3.00000"
        b"                       \n"
        b"  VARIABLE      total     *          total        4.00000"
        b"                       \n"
        b"      RULE              POS 0.000000                 total\n"
        b"      RULE              POS 0.000000              daycurve\n"
        b"    pump.2                                      0\n"
        b"  VARIABLE      total     =        5.00000"
        b"                                      \n"
        b"      RULE              POS 0.000000                 total\n"
        b"      RULE              POS 0.000000               wkcurve\n"
        b"TERMINATOR\n"
    )


@pytest.mark.parametrize(
    "name", ["", "  ", "a\nb", "a\rb", None, 1, True, [], b"title"]
)
def test_creator_rejects_invalid_document_name(name: object) -> None:
    with pytest.raises(RTCValidationError):
        RTCCreator(name)  # type: ignore[arg-type]


@pytest.mark.parametrize("existing", [True, False])
def test_creator_table_source_validation_does_not_touch_destination(
    tmp_path: Path,
    existing: bool,
) -> None:
    path = tmp_path / "control.rtc"
    if existing:
        path.write_bytes(b"keep me")
    rtc = RTCCreator("Control")
    level = rtc.range_("level", RangeType.LEVEL, "node.1")
    with pytest.raises(RTCValidationError, match="numeric source"):
        rtc.table("curve", level, TableType.STEP, [(time(6), 1)])
    if existing:
        assert path.read_bytes() == b"keep me"
    else:
        assert not path.exists()
    # The failed table neither appends a line nor reserves its name.
    rtc.table("curve", level, TableType.STEP, [(0, 1)])
    _finish(rtc)
    rtc.write(path)
    assert path.read_text().count("     TABLE") == 1


def test_creator_requires_end_before_writing(tmp_path: Path) -> None:
    rtc = RTCCreator("Control")
    rtc.regulator("pump.1")
    rtc.rule(RuleType.POSITION)
    path = tmp_path / "control.rtc"
    with pytest.raises(RTCValidationError, match="end"):
        rtc.write(path)
    assert not path.exists()


def test_creator_validate_and_render_allow_continued_editing(tmp_path: Path) -> None:
    rtc = RTCCreator("Contr\u00f4le")
    rtc.regulator("pump.1")
    rtc.rule(RuleType.POSITION)

    assert rtc.validate() is None
    preview = rtc.render()
    assert rtc.render() == preview
    assert preview.endswith("TERMINATOR\n")
    assert "\r" not in preview
    assert "Contr\u00f4le" in preview
    rtc.comment("D\u00e9bit")
    assert rtc.validate() is None
    updated = rtc.render()
    assert updated != preview

    path = tmp_path / "control.rtc"
    with pytest.raises(RTCValidationError, match="finished with end"):
        rtc.write(path)
    assert not path.exists()
    rtc.end()
    assert rtc.validate() is None
    assert rtc.render() == updated
    rtc.write(path)
    assert path.read_bytes() == updated.encode("utf-8")


@pytest.mark.parametrize("method", ["validate", "render"])
@pytest.mark.parametrize("missing_regulator", [False, True])
def test_creator_check_failure_leaves_document_editable(
    method: str, missing_regulator: bool
) -> None:
    rtc = RTCCreator("Control")
    if not missing_regulator:
        rtc.regulator("pump.1")
    message = "at least one regulator" if missing_regulator else "at least one rule"
    with pytest.raises(RTCValidationError, match=message):
        if method == "validate":
            rtc.validate()
        else:
            rtc.render()

    if missing_regulator:
        rtc.regulator("pump.1")
    rtc.rule(RuleType.POSITION)
    rtc.validate()
    assert rtc.render().endswith("TERMINATOR\n")


def test_creator_validate_and_render_reject_incomplete_ended_document() -> None:
    rtc = RTCCreator("Control")
    rtc.regulator("pump.1")
    rtc.end()
    with pytest.raises(RTCValidationError, match="at least one rule"):
        rtc.validate()
    with pytest.raises(RTCValidationError, match="at least one rule"):
        rtc.render()
    with pytest.raises(RTCValidationError, match="already ended"):
        rtc.rule(RuleType.POSITION)


@pytest.mark.parametrize("line_break", ["\n", "\r", "\r\n"])
@pytest.mark.parametrize(
    "field",
    [
        "document",
        "comment",
        "range",
        "location",
        "variable",
        "table",
        "logic",
        "controller",
        "regulator",
        "table_measurement",
        "variable_measurement",
    ],
)
def test_creator_rejects_record_breaking_text_without_changing_document(
    field: str, line_break: str
) -> None:
    value = f"a{line_break}b"
    if field == "document":
        with pytest.raises(RTCValidationError, match="single line"):
            RTCCreator(value)
        return

    rtc = RTCCreator("Control")
    source = rtc.range_("level", RangeType.LEVEL, "node.1")
    rtc.regulator("pump.1")
    rtc.rule(RuleType.POSITION)
    before = rtc.render()
    with pytest.raises(RTCValidationError, match="single line|newlines|line breaks"):
        if field == "comment":
            rtc.comment(value)
        elif field == "range":
            rtc.range_(value, RangeType.LEVEL, "node.1")
        elif field == "location":
            rtc.range_("local", RangeType.LEVEL, value)
        elif field == "variable":
            rtc.variable(value)
        elif field == "table":
            rtc.table(value, source, TableType.STEP, [(0, 1)])
        elif field == "logic":
            rtc.logic(value, LogicOperator.NOT, source)
        elif field == "controller":
            rtc.controller(value, ControllerType.INCREMENTAL, 60)
        elif field == "regulator":
            rtc.regulator(value)
        elif field == "table_measurement":
            rtc.table("lookup", source, TableType.STEP, [(0, 1)], value)
        else:
            rtc.variable("total", VariableOperator.ASSIGN, 1, measurement=value)
    assert rtc.render() == before


def test_creator_rejects_repeated_end() -> None:
    rtc = RTCCreator("Control")
    rtc.end()
    with pytest.raises(RTCValidationError, match="already ended"):
        rtc.end()


@pytest.mark.parametrize(
    "method",
    [
        "comment",
        "range_",
        "variable",
        "table",
        "logic",
        "controller",
        "regulator",
        "rule",
    ],
)
def test_creator_rejects_every_element_after_end(method: str) -> None:
    rtc = RTCCreator("Control")
    source = rtc.range_("level", RangeType.LEVEL, "node.1")
    rtc.end()
    with pytest.raises(RTCValidationError, match="already ended"):
        if method == "comment":
            rtc.comment("Note")
        elif method == "range_":
            rtc.range_("other", RangeType.LEVEL, "node.1")
        elif method == "variable":
            rtc.variable("var", VariableOperator.ASSIGN, 1)
        elif method == "table":
            rtc.table("tab", source, TableType.STEP, [(0, 1)])
        elif method == "logic":
            rtc.logic("logic", LogicOperator.NOT, source)
        elif method == "controller":
            rtc.controller("inc", ControllerType.INCREMENTAL, 60)
        elif method == "regulator":
            rtc.regulator("pump.1")
        else:
            rtc.rule(RuleType.POSITION)


@pytest.mark.parametrize("existing", [True, False])
def test_creator_validation_does_not_touch_destination(
    tmp_path: Path, existing: bool
) -> None:
    path = tmp_path / "control.rtc"
    if existing:
        path.write_bytes(b"keep me")
    rtc = RTCCreator("Control")
    rtc.regulator("pump.1")
    rtc.end()
    with pytest.raises(RTCValidationError, match="at least one rule"):
        rtc.write(path)
    if existing:
        assert path.read_bytes() == b"keep me"
    else:
        assert not path.exists()


def test_creator_failed_model_validation_does_not_append(tmp_path: Path) -> None:
    rtc = RTCCreator("Control")
    with pytest.raises(RTCValidationError):
        rtc.comment("")
    _finish(rtc)
    path = tmp_path / "control.rtc"
    rtc.write(path)
    assert len(path.read_text().splitlines()) == 5


def test_creator_writes_utf8_and_can_write_again(tmp_path: Path) -> None:
    rtc = RTCCreator("Contr\u00f4le")
    rtc.comment("D\u00e9bit")
    _finish(rtc)
    first, second = tmp_path / "first.rtc", tmp_path / "second.rtc"
    second.write_bytes(b"old")
    rtc.write(first)
    rtc.write(second)
    assert first.read_bytes() == second.read_bytes()
    assert "Contr\u00f4le".encode() in first.read_bytes()
    assert b"\r" not in first.read_bytes()
    assert first.read_bytes().count(b"TERMINATOR\n") == 1


def test_creator_propagates_filesystem_errors(tmp_path: Path) -> None:
    rtc = RTCCreator("Control")
    _finish(rtc)
    with pytest.raises(FileNotFoundError):
        rtc.write(tmp_path / "missing" / "control.rtc")


def test_public_exports_include_only_creator_returned_models_and_options() -> None:
    assert rtc_infoworks_icm.__all__ == [
        "Controller",
        "ControllerType",
        "Logic",
        "LogicOperator",
        "Range",
        "RangeType",
        "RTCCreator",
        "RTCValidationError",
        "RuleType",
        "Table",
        "TableType",
        "Variable",
        "VariableOperator",
    ]
    for name in (
        "Rule",
        "Comment",
        "Regulator",
        "Reference",
        "VariableAssignment",
        "TableRow",
        "WeeklyTime",
    ):
        assert not hasattr(rtc_infoworks_icm, name)


def test_creator_signatures_require_enums() -> None:
    variable_overloads = get_overloads(RTCCreator.variable)
    assert get_type_hints(variable_overloads[1])["operator"] is VariableOperator
    for method, parameter, expected in (
        (RTCCreator.range_, "type", RangeType),
        (RTCCreator.table, "type", TableType),
        (RTCCreator.logic, "operator", LogicOperator),
        (RTCCreator.controller, "type", ControllerType),
        (RTCCreator.rule, "type", RuleType),
    ):
        assert get_type_hints(method)[parameter] == expected


def test_creator_converts_weekly_time_and_copies_table_pairs(tmp_path: Path) -> None:
    rows = [((1, time(6)), 0.2), ((2, time(6)), 0.8)]
    rtc = RTCCreator("Weekly")
    week = rtc.range_(
        "week", RangeType.TIME_REPEAT, minimum=(1, time(6)), maximum=(2, time(6))
    )
    curve = rtc.table("curve", week, TableType.STEP, rows)
    rows[0] = ((1, time(6)), 9)
    rtc.regulator("pump.1")
    rtc.rule(RuleType.POSITION, variable_value=curve)
    rtc.end()
    path = tmp_path / "weekly.rtc"
    rtc.write(path)
    content = path.read_text()
    assert "01000000060000 02000000060000\n" in content
    assert "01000000060000          0.200\n" in content
    assert "02000000060000          0.800\n" in content


def test_creator_accepts_calendar_and_daily_time_bounds(tmp_path: Path) -> None:
    rtc = RTCCreator("Times")
    date = rtc.range_("date", RangeType.TIME, minimum=datetime(2026, 1, 1, 6))
    rtc.range_("daily", RangeType.TIME_REPEAT, minimum=time(6))
    rtc.regulator("pump.1")
    rtc.rule(RuleType.SWITCH_ON, condition=date)
    rtc.end()
    path = tmp_path / "times.rtc"
    rtc.write(path)
    assert "01012026060000" in path.read_text()
    assert "00000000060000" in path.read_text()


def test_variable_identity_and_assignments_are_explicit_and_stable(
    tmp_path: Path,
) -> None:
    rtc = RTCCreator("Variables")
    total = rtc.variable("total")
    rtc.variable("unused")
    assert rtc.variable(total, VariableOperator.ADD, total, 100) is total
    assert rtc.variable(total, VariableOperator.MULTIPLY, total, 2) is total
    rtc.range_("value", RangeType.VARIABLE, location=total)
    rtc.regulator("pump.1")
    rtc.rule(RuleType.POSITION, variable_value=total)
    rtc.end()
    path = tmp_path / "variables.rtc"
    rtc.write(path)
    text = path.read_text()
    assert "unused" not in text
    assert text.count("  VARIABLE") == 2
    lines = [line for line in text.splitlines() if line.startswith("  VARIABLE")]
    assert "     +          total      100.00000" in lines[0]
    assert "     *          total        2.00000" in lines[1]
    assert "     RANGE      value   VAR      total" in text
    assert not hasattr(total, "value")
    assert not hasattr(total, "operator")
    with pytest.raises(FrozenInstanceError):
        total.name = "other"  # type: ignore[misc]


def test_invalid_conversion_does_not_append(tmp_path: Path) -> None:
    rtc = RTCCreator("Control")
    rtc.regulator("pump.1")
    with pytest.raises(RTCValidationError, match="rule type"):
        rtc.rule("unknown")  # type: ignore[arg-type]
    with pytest.raises(RTCValidationError, match="weekday"):
        rtc.range_("bad", RangeType.TIME_REPEAT, minimum=(8, time()))
    rtc.rule(RuleType.POSITION)
    rtc.end()
    path = tmp_path / "control.rtc"
    rtc.write(path)
    assert len(path.read_text().splitlines()) == 5


def test_creator_rejects_numeric_strings_as_operands() -> None:
    rtc = RTCCreator("References")
    rtc.variable("1", VariableOperator.ASSIGN, 2)
    with pytest.raises(RTCValidationError, match="argument 1 must be"):
        rtc.variable("target", VariableOperator.ASSIGN, "1")  # type: ignore[arg-type]
    rtc.variable("target", VariableOperator.ASSIGN, 1)


@pytest.mark.parametrize("bound", ["minimum", "maximum"])
def test_creator_rejects_malformed_weekly_bounds(bound: str) -> None:
    rtc = RTCCreator("Control")
    with pytest.raises(RTCValidationError, match="pair"):
        if bound == "minimum":
            rtc.range_("week", RangeType.TIME_REPEAT, minimum=(1,))  # type: ignore[arg-type]
        else:
            rtc.range_("week", RangeType.TIME_REPEAT, maximum=(1,))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "rows",
    [
        None,
        "rows",
        [1],
        [(1,)],
        [(1, 2, 3)],
        ["12"],
        [[0, 1]],
        [(None, 1)],
        [((1,), 2)],
    ],
)
def test_creator_rejects_malformed_table_inputs(rows: object) -> None:
    rtc = RTCCreator("Control")
    level = rtc.range_("level", RangeType.LEVEL, "node.1")
    with pytest.raises(RTCValidationError):
        rtc.table("curve", level, TableType.STEP, rows)  # type: ignore[arg-type]
    rtc.table("curve", level, TableType.STEP, [(0, 1)])


@pytest.mark.parametrize("tuple_rows", [False, True])
def test_creator_accepts_list_or_tuple_of_table_row_tuples(
    tmp_path: Path, tuple_rows: bool
) -> None:
    rtc = RTCCreator("Control")
    level = rtc.range_("level", RangeType.LEVEL, "node.1")
    rows = [(0, 0.2), (10, 0.8)]
    curve = rtc.table(
        "curve", level, TableType.STEP, tuple(rows) if tuple_rows else rows
    )
    rtc.regulator("pump.1")
    rtc.rule(RuleType.POSITION, variable_value=curve)
    rtc.end()
    path = tmp_path / "table.rtc"
    rtc.write(path)
    content = path.read_text()
    assert "         0.000          0.200\n" in content
    assert "        10.000          0.800\n" in content


def _readers(rtc: RTCCreator, value: Variable) -> tuple[Callable[[], object], ...]:
    return (
        lambda: rtc.variable("read", VariableOperator.ASSIGN, value),
        lambda: rtc.range_("read", RangeType.VARIABLE, value),
        lambda: rtc.table("read", value, TableType.STEP, [(0, 1)]),
        lambda: rtc.rule(RuleType.POSITION, variable_value=value),
    )


@pytest.mark.parametrize("surface", range(4))
def test_variable_must_be_assigned_before_other_records(surface: int) -> None:
    rtc = RTCCreator("Control")
    rtc.regulator("pump.1")
    total = rtc.variable("total")
    reader = _readers(rtc, total)[surface]
    with pytest.raises(RTCValidationError, match="first assignment"):
        reader()
    assert rtc.variable(total, VariableOperator.ADD, total, 1) is total
    reader()


@pytest.mark.parametrize("failure", ["field", "foreign", "unassigned"])
def test_failed_creation_and_first_assignment_are_atomic(
    tmp_path: Path, failure: str
) -> None:
    rtc = RTCCreator("Control")
    if failure == "field":
        with pytest.raises(RTCValidationError):
            rtc.variable("total", VariableOperator.ADD, 1)
    else:
        source = Variable("source") if failure == "foreign" else rtc.variable("source")
        with pytest.raises(RTCValidationError):
            rtc.variable("total", VariableOperator.ASSIGN, source)
    total = rtc.variable("total")
    with pytest.raises(RTCValidationError):
        rtc.variable(total, VariableOperator.ADD, total)
    with pytest.raises(RTCValidationError, match="first assignment"):
        rtc.variable("read", VariableOperator.ASSIGN, total)
    rtc.variable(total, VariableOperator.ASSIGN, 1)
    rtc.variable("read", VariableOperator.ASSIGN, total)
    _finish(rtc)
    path = tmp_path / "atomic.rtc"
    rtc.write(path)
    assert path.read_text().count("  VARIABLE") == 2


def test_global_variable_can_be_read_but_not_updated_in_regulator() -> None:
    rtc = RTCCreator("Control")
    total = rtc.variable("total", VariableOperator.ASSIGN, 1)
    rtc.regulator("pump.1")
    with pytest.raises(RTCValidationError, match="creation scope"):
        rtc.variable(total, VariableOperator.ADD, total, 1)
    rtc.rule(RuleType.POSITION, variable_value=total)
    rtc.regulator("pump.2")
    rtc.rule(RuleType.POSITION, variable_value=total)


def test_scope_changes_and_shadowing_are_transactional(tmp_path: Path) -> None:
    rtc = RTCCreator("Control")
    global_level = rtc.range_("level", RangeType.LEVEL, "node.1")
    rtc.regulator("pump.1")
    local_level = rtc.range_("level", RangeType.LEVEL, "node.2")
    with pytest.raises(RTCValidationError, match="at least one rule"):
        rtc.regulator("pump.2")
    with pytest.raises(RTCValidationError, match="shadowed"):
        rtc.rule(RuleType.POSITION, condition=global_level)
    rtc.rule(RuleType.POSITION, condition=local_level)
    with pytest.raises(RTCValidationError, match="duplicate regulator"):
        rtc.regulator("pump.1")
    rtc.regulator("pump.2")
    with pytest.raises(RTCValidationError, match="scope"):
        rtc.rule(RuleType.POSITION, condition=local_level)
    rtc.rule(RuleType.POSITION, condition=global_level)
    rtc.end()
    rtc.write(tmp_path / "scopes.rtc")


@pytest.mark.parametrize("surface", range(8))
def test_creator_rejects_foreign_objects_on_every_reference_surface(
    surface: int,
) -> None:
    rtc = RTCCreator("Control")
    rtc.range_("level", RangeType.LEVEL, "node.1")
    foreign = RTCCreator("Other")
    level = foreign.range_("level", RangeType.LEVEL, "node.1")
    pid = foreign.controller("pid", ControllerType.PID, 60, level)
    rtc.regulator("pump.1")
    operations: tuple[Callable[[], object], ...] = (
        lambda: rtc.logic("high", LogicOperator.NOT, level),
        lambda: rtc.table("curve", level, TableType.STEP, [(0, 1)]),
        lambda: rtc.variable("value", VariableOperator.ASSIGN, level),
        lambda: rtc.range_("value", RangeType.VARIABLE, level),
        lambda: rtc.controller("pid", ControllerType.PID, 60, level),
        lambda: rtc.rule(RuleType.POSITION, condition=level),
        lambda: rtc.rule(RuleType.CONTROL, controller=pid),
        lambda: rtc.rule(RuleType.POSITION, variable_value=level),
    )
    with pytest.raises(RTCValidationError, match="foreign"):
        operations[surface]()
    rtc.rule(RuleType.POSITION)


@pytest.mark.parametrize("surface", range(8))
def test_creator_rejects_name_only_references(surface: int) -> None:
    rtc = RTCCreator("Control")
    rtc.regulator("pump.1")
    with pytest.raises(RTCValidationError):
        if surface == 0:
            rtc.logic("high", LogicOperator.NOT, "level")  # type: ignore[arg-type]
        elif surface == 1:
            rtc.table("curve", "level", TableType.STEP, [(0, 1)])  # type: ignore[arg-type]
        elif surface == 2:
            rtc.variable("value", VariableOperator.ASSIGN, "level")  # type: ignore[arg-type]
        elif surface == 3:
            rtc.range_("value", RangeType.VARIABLE, "level")
        elif surface == 4:
            rtc.controller("pid", ControllerType.PID, 60, "level")  # type: ignore[arg-type]
        elif surface == 5:
            rtc.rule(RuleType.POSITION, condition="level")  # type: ignore[arg-type]
        elif surface == 6:
            rtc.rule(RuleType.CONTROL, controller="pid")  # type: ignore[arg-type]
        else:
            rtc.rule(RuleType.POSITION, variable_value="level")  # type: ignore[arg-type]


def test_second_same_name_variable_is_not_an_update() -> None:
    rtc = RTCCreator("Control")
    total = rtc.variable("total")
    with pytest.raises(RTCValidationError, match="duplicate definition"):
        rtc.variable("total", VariableOperator.ASSIGN, 1)
    assert rtc.variable(total, VariableOperator.ASSIGN, 1) is total


def test_existing_variable_requires_explicit_operation() -> None:
    rtc = RTCCreator("Control")
    total = rtc.variable("total")
    with pytest.raises(RTCValidationError, match="requires an operator"):
        rtc.variable(total)  # type: ignore[call-overload]
    with pytest.raises(RTCValidationError, match="requires argument 2"):
        rtc.variable(total, VariableOperator.ADD, 100)


@pytest.mark.parametrize("with_operand", [False, True])
def test_explicit_none_operator_does_not_create_identity(with_operand: bool) -> None:
    rtc = RTCCreator("Control")
    with pytest.raises(RTCValidationError):
        if with_operand:
            rtc.variable("total", None, 1)  # type: ignore[call-overload]
        else:
            rtc.variable("total", None)  # type: ignore[call-overload]
    rtc.variable("total", VariableOperator.ASSIGN, 1)


def test_identity_only_creation_rejects_assignment_fields_without_operator() -> None:
    rtc = RTCCreator("Control")
    with pytest.raises(RTCValidationError, match="requires an operator"):
        rtc.variable("total", argument_1=1)  # type: ignore[call-overload]
    with pytest.raises(RTCValidationError, match="requires an operator"):
        rtc.variable("total", measurement="m")  # type: ignore[call-overload]
    rtc.variable("total")


@pytest.mark.parametrize("existing", [False, True])
def test_write_replays_ordered_validation_before_opening_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing: bool,
) -> None:
    from rtc_infoworks_icm.elements.regulator import Regulator
    from rtc_infoworks_icm.elements.rule import Rule
    from rtc_infoworks_icm.reference import Reference

    rtc = RTCCreator("Control")
    _finish(rtc)
    foreign = Range("foreign", RangeType.LEVEL, "node.1")
    monkeypatch.setattr(
        rtc,
        "_elements",
        [
            Regulator("pump.1"),
            Rule(RuleType.POSITION, condition=Reference(foreign)),
        ],
    )
    path = tmp_path / "final-validation.rtc"
    if existing:
        path.write_bytes(b"keep me")
    with pytest.raises(RTCValidationError, match="foreign"):
        rtc.write(path)
    if existing:
        assert path.read_bytes() == b"keep me"
    else:
        assert not path.exists()


def test_invalid_update_leaves_prior_assignments_unchanged(tmp_path: Path) -> None:
    rtc = RTCCreator("Control")
    total = rtc.variable("total", VariableOperator.ASSIGN, 100, measurement="m")
    with pytest.raises(RTCValidationError):
        rtc.variable(total, VariableOperator.ADD, total, float("inf"))
    rtc.variable(total, VariableOperator.SUBTRACT, total, 10, measurement="mm")
    _finish(rtc)
    path = tmp_path / "updates.rtc"
    rtc.write(path)
    lines = [
        line for line in path.read_text().splitlines() if line.startswith("  VARIABLE")
    ]
    assert len(lines) == 2
    assert "100.00000" in lines[0] and lines[0].endswith("      M")
    assert "10.00000" in lines[1] and lines[1].endswith("     MM")
