from datetime import datetime, time
from pathlib import Path
from typing import get_type_hints

import pytest

import rtc_infoworks_icm
from rtc_infoworks_icm import (
    ControllerType,
    LogicOperator,
    RangeType,
    RTCCreator,
    RTCValidationError,
    RuleType,
    TableType,
    VariableOperator,
)


def test_creator_writes_exact_minimal_document(tmp_path: Path) -> None:
    path = tmp_path / "control.rtc"
    rtc = RTCCreator("Example")

    assert rtc.regulator("pump.1") is rtc
    assert rtc.rule(RuleType.POSITION) is rtc
    assert rtc.end() is rtc
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
    assert rtc.comment("Global definitions") is rtc
    assert rtc.range_("level", RangeType.LEVEL, "node.1", 1, 2, 4) is rtc
    assert rtc.variable("value", VariableOperator.ASSIGN, 1) is rtc
    assert rtc.table("lookup", "level", TableType.STEP, [(1, 2)], "FLOW") is rtc
    assert rtc.logic("high", LogicOperator.NOT, "level") is rtc
    assert (
        rtc.controller("pid", ControllerType.PID, 60, "level", 0.5, -1, 0.1, 0.05)
        is rtc
    )
    assert rtc.regulator("pump.1", -1, 0.1, 0.2, 0.3, True) is rtc
    assert (
        rtc.rule(
            RuleType.CONTROL,
            "high",
            "pid",
            1,
            "lookup",
        )
        is rtc
    )
    rtc.end()
    path = tmp_path / "control.rtc"
    rtc.write(str(path))

    lines = path.read_text().splitlines()
    assert lines[2] == "   COMMENT Global definitions"
    assert lines[3].startswith("     RANGE")
    assert lines[4].startswith("  VARIABLE")
    assert lines[5].startswith("     TABLE")
    assert lines[-5].startswith("     LOGIC")
    assert lines[-4].startswith("CONTROLLER")
    assert lines[-3] == "    pump.1 -1.00000 0.200000 0.100000 0.300000  1"
    assert lines[-2].startswith("      RULE")
    assert lines[-1] == "TERMINATOR"


@pytest.mark.parametrize("name", ["", "  ", "a\nb", "a\rb"])
def test_creator_rejects_invalid_document_name(name: str) -> None:
    with pytest.raises(RTCValidationError):
        RTCCreator(name)


@pytest.mark.parametrize("name", [None, 1, True, [], b"title"])
def test_creator_rejects_nontext_document_name(name: object) -> None:
    with pytest.raises(RTCValidationError, match="document name must be text"):
        RTCCreator(name)  # type: ignore[arg-type]


@pytest.mark.parametrize("existing", [True, False])
def test_creator_table_source_validation_does_not_touch_destination(
    tmp_path: Path, existing: bool
) -> None:
    path = tmp_path / "control.rtc"
    if existing:
        path.write_bytes(b"keep me")
    rtc = RTCCreator("Control")
    rtc.range_("level", RangeType.LEVEL, "node.1")
    rtc.table("curve", "level", TableType.STEP, [(time(6), 1)])
    rtc.regulator("pump.1").rule(RuleType.POSITION).end()
    with pytest.raises(RTCValidationError, match="numeric source"):
        rtc.write(path)
    if existing:
        assert path.read_bytes() == b"keep me"
    else:
        assert not path.exists()


def test_creator_requires_end_before_writing(tmp_path: Path) -> None:
    path = tmp_path / "control.rtc"
    rtc = RTCCreator("Control").regulator("pump.1").rule(RuleType.POSITION)
    with pytest.raises(RTCValidationError, match="end"):
        rtc.write(path)
    assert not path.exists()


def test_creator_rejects_repeated_end() -> None:
    rtc = RTCCreator("Control").end()
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
    rtc = RTCCreator("Control").end()
    with pytest.raises(RTCValidationError, match="already ended"):
        if method == "comment":
            rtc.comment("Note")
        elif method == "range_":
            rtc.range_("level", RangeType.LEVEL, "node.1")
        elif method == "variable":
            rtc.variable("var", VariableOperator.ASSIGN, 1)
        elif method == "table":
            rtc.table("tab", "var", TableType.STEP, [(0, 1)])
        elif method == "logic":
            rtc.logic("logic", LogicOperator.NOT, "level")
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
    rtc = RTCCreator("Control").regulator("pump.1").end()
    with pytest.raises(RTCValidationError, match="at least one rule"):
        rtc.write(path)
    if existing:
        assert path.read_bytes() == b"keep me"
    else:
        assert not path.exists()


def test_creator_failed_model_validation_does_not_append(tmp_path: Path) -> None:
    rtc = RTCCreator("Control").regulator("pump.1")
    with pytest.raises(RTCValidationError):
        rtc.comment("")
    rtc.rule(RuleType.POSITION).end()
    path = tmp_path / "control.rtc"
    rtc.write(path)
    assert len(path.read_text().splitlines()) == 5


def test_creator_writes_utf8_and_can_write_again(tmp_path: Path) -> None:
    rtc = (
        RTCCreator("Contr\u00f4le")
        .comment("D\u00e9bit")
        .regulator("pump.1")
        .rule(RuleType.POSITION)
        .end()
    )
    first, second = tmp_path / "first.rtc", tmp_path / "second.rtc"
    second.write_bytes(b"old")
    rtc.write(first)
    rtc.write(second)
    assert first.read_bytes() == second.read_bytes()
    assert "Contr\u00f4le".encode() in first.read_bytes()
    assert b"\r" not in first.read_bytes()
    assert first.read_bytes().count(b"TERMINATOR\n") == 1


def test_creator_propagates_filesystem_errors(tmp_path: Path) -> None:
    rtc = RTCCreator("Control").regulator("pump.1").rule(RuleType.POSITION).end()
    with pytest.raises(FileNotFoundError):
        rtc.write(tmp_path / "missing" / "control.rtc")


def test_public_exports_are_minimal() -> None:
    assert rtc_infoworks_icm.__all__ == [
        "ControllerType",
        "LogicOperator",
        "RangeType",
        "RTCCreator",
        "RTCValidationError",
        "RuleType",
        "TableType",
        "VariableOperator",
    ]
    for name in (
        "Range",
        "Rule",
        "Controller",
        "Variable",
        "Table",
        "Logic",
        "Comment",
        "Regulator",
        "Reference",
        "TableRow",
        "WeeklyTime",
    ):
        assert not hasattr(rtc_infoworks_icm, name)


def test_creator_signatures_require_enums() -> None:
    for method, parameter, expected in (
        (RTCCreator.variable, "operator", VariableOperator),
        (RTCCreator.range_, "type", RangeType),
        (RTCCreator.table, "type", TableType),
        (RTCCreator.logic, "operator", LogicOperator),
        (RTCCreator.controller, "type", ControllerType),
        (RTCCreator.rule, "type", RuleType),
    ):
        assert get_type_hints(method)[parameter] == expected


def test_creator_converts_weekly_time_and_table_pairs(tmp_path: Path) -> None:
    rows = [((1, time(6)), 0.2), ((2, time(6)), 0.8)]
    rtc = RTCCreator("Weekly")
    rtc.range_(
        "week", RangeType.TIME_REPEAT, minimum=(1, time(6)), maximum=(2, time(6))
    )
    rtc.table("curve", "week", TableType.STEP, rows)
    rows[0] = ((1, time(6)), 9)
    rtc.regulator("pump.1").rule(RuleType.POSITION, variable_value="curve").end()
    path = tmp_path / "weekly.rtc"
    rtc.write(path)
    content = path.read_text()
    assert "01000000060000 02000000060000\n" in content
    assert "01000000060000          0.200\n" in content
    assert "02000000060000          0.800\n" in content


def test_creator_accepts_calendar_and_daily_time_bounds(tmp_path: Path) -> None:
    rtc = RTCCreator("Times")
    rtc.range_("date", RangeType.TIME, minimum=datetime(2026, 1, 1, 6))
    rtc.range_("daily", RangeType.TIME_REPEAT, minimum=time(6))
    rtc.regulator("pump.1").rule(RuleType.SWITCH_ON, condition="date").end()
    path = tmp_path / "times.rtc"
    rtc.write(path)
    assert "01012026060000" in path.read_text()
    assert "00000000060000" in path.read_text()


def test_creator_accepts_named_variable_arguments(tmp_path: Path) -> None:
    rtc = RTCCreator("Variables")
    rtc.variable("total", VariableOperator.ADD, "total", 1)
    rtc.range_("value", RangeType.VARIABLE, location="total")
    rtc.regulator("pump.1").rule(RuleType.POSITION, variable_value="total").end()
    rtc.write(tmp_path / "variables.rtc")


def test_invalid_conversion_does_not_append(tmp_path: Path) -> None:
    rtc = RTCCreator("Control").regulator("pump.1")
    with pytest.raises(RTCValidationError, match="rule type"):
        rtc.rule("unknown")  # type: ignore[arg-type]
    with pytest.raises(RTCValidationError, match="weekday"):
        rtc.range_("bad", RangeType.TIME_REPEAT, minimum=(8, time()))
    rtc.rule(RuleType.POSITION).end()
    path = tmp_path / "control.rtc"
    rtc.write(path)
    assert len(path.read_text().splitlines()) == 5


def test_creator_treats_numeric_strings_as_reference_names(tmp_path: Path) -> None:
    rtc = RTCCreator("References")
    rtc.variable("1", VariableOperator.ASSIGN, 2)
    rtc.variable("target", VariableOperator.ASSIGN, "1")
    rtc.regulator("pump.1").rule(RuleType.POSITION, variable_value="target").end()
    path = tmp_path / "references.rtc"
    rtc.write(path)
    target_line = next(
        line
        for line in path.read_text().splitlines()
        if "target" in line and "VARIABLE" in line
    )
    assert "             1" in target_line
    assert "1.00000" not in target_line


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
    with pytest.raises(RTCValidationError):
        RTCCreator("Control").table("curve", "level", TableType.STEP, rows)  # type: ignore[arg-type]


@pytest.mark.parametrize("tuple_rows", [False, True])
def test_creator_accepts_list_or_tuple_of_table_row_tuples(
    tmp_path: Path, tuple_rows: bool
) -> None:
    rtc = RTCCreator("Control")
    rtc.range_("level", RangeType.LEVEL, "node.1")
    rows = [(0, 0.2), (10, 0.8)]
    rtc.table("curve", "level", TableType.STEP, tuple(rows) if tuple_rows else rows)
    rtc.regulator("pump.1").rule(RuleType.POSITION, variable_value="curve").end()
    path = tmp_path / "table.rtc"
    rtc.write(path)
    content = path.read_text()
    assert "         0.000          0.200\n" in content
    assert "        10.000          0.800\n" in content
