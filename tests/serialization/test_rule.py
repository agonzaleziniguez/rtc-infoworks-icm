from rtc_infoworks_icm._serialization.rule import serialize_rule
from rtc_infoworks_icm.elements.rule import Rule, RuleType
from rtc_infoworks_icm.reference import Reference


def test_serialize_position_rule_with_condition() -> None:
    rule = Rule(RuleType.POSITION, condition=Reference("hi_level"), fixed_value=1.0)

    assert serialize_rule(rule) == (
        "      RULE   hi_level   POS   1.0000                      \n"
    )


def test_serialize_control_rule_with_controller_and_variable_value() -> None:
    rule = Rule(
        RuleType.CONTROL,
        controller=Reference("pid1"),
        variable_value=Reference("setpoint"),
    )

    assert serialize_rule(rule) == (
        "      RULE             CTRL 0.000000       pid1   setpoint\n"
    )
