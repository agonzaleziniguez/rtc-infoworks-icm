import pytest

from rtc_infoworks_icm.elements.rule import Rule, RuleType
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


def test_rule_preserves_values() -> None:
    rule = Rule(
        RuleType.POSITION,
        condition=Reference("hi_level"),
        fixed_value=1.5,
    )

    assert rule.type is RuleType.POSITION
    assert rule.condition == Reference("hi_level")
    assert rule.fixed_value == 1.5
    assert rule.controller is None
    assert rule.variable_value is None


def test_rule_defaults_to_blank_condition_and_zero_value() -> None:
    rule = Rule(RuleType.POSITION)

    assert rule.condition is None
    assert rule.fixed_value == 0.0


@pytest.mark.parametrize("value", [True, float("inf"), float("-inf"), float("nan")])
def test_rule_rejects_invalid_fixed_value(value: float) -> None:
    with pytest.raises(RTCValidationError):
        Rule(RuleType.POSITION, fixed_value=value)


def test_rule_rejects_fixed_value_that_does_not_fit() -> None:
    with pytest.raises(RTCValidationError, match="does not fit the RTC field"):
        Rule(RuleType.POSITION, fixed_value=123_456.0)


def test_rule_rejects_controller_on_non_control_type() -> None:
    with pytest.raises(RTCValidationError, match="only used with control-type"):
        Rule(RuleType.POSITION, controller=Reference("pid1"))


def test_control_rule_allows_controller() -> None:
    rule = Rule(RuleType.CONTROL, controller=Reference("pid1"))
    assert rule.controller == Reference("pid1")
