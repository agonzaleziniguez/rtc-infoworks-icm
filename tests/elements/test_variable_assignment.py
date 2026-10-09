from dataclasses import FrozenInstanceError

import pytest

from rtc_infoworks_icm.elements.variable import (
    Variable,
    VariableAssignment,
    VariableOperator,
)
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference


def test_variable_identity_is_stable_and_distinct_by_identity() -> None:
    first = Variable("total")
    second = Variable("total")
    assert first.name == second.name
    assert first != second
    assert len({first, second}) == 2
    assert not hasattr(first, "operator")
    assert not hasattr(first, "value")


@pytest.mark.parametrize("name", ["", " ", "12345678901", None, 123])
def test_variable_identity_validates_name(name: object) -> None:
    with pytest.raises(RTCValidationError, match="variable name"):
        Variable(name)  # type: ignore[arg-type]


def test_reference_holds_actual_target_and_derives_name() -> None:
    target = Variable("total")
    reference = Reference(target)
    assert reference.target is target
    assert reference.name == target.name
    assert reference == Reference(target)
    assert reference != Reference(Variable("total"))


@pytest.mark.parametrize("target", ["total", Reference(Variable("total")), None, 1, []])
def test_object_reference_rejects_non_target_objects(target: object) -> None:
    with pytest.raises(RTCValidationError, match="referenceable object"):
        Reference(target)  # type: ignore[arg-type]


def test_first_assignment_can_reference_its_own_identity() -> None:
    target = Variable("total")
    reference = Reference(target)
    operation = VariableAssignment(target, VariableOperator.ADD, reference, 1)
    assert operation.target is target
    assert operation.argument_1 is reference
    assert operation.name == "total"


def test_repeated_assignments_share_identity_and_preserve_record_fields() -> None:
    target = Variable("total")
    first = VariableAssignment(target, VariableOperator.ASSIGN, 100, measurement="m")
    second = VariableAssignment(
        target, VariableOperator.SUBTRACT, Reference(target), 10, measurement="mm"
    )
    assert first.target is second.target
    assert first.operator is VariableOperator.ASSIGN
    assert first.argument_1 == 100
    assert first.measurement == "m"
    assert second.measurement == "mm"


def test_identity_reference_and_assignment_are_immutable() -> None:
    target = Variable("total")
    reference = Reference(target)
    assignment = VariableAssignment(target, VariableOperator.ASSIGN, 1)
    with pytest.raises(FrozenInstanceError):
        target.name = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        reference.target = Variable("other")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        assignment.argument_1 = 2  # type: ignore[misc]


@pytest.mark.parametrize("target", ["total", Reference(Variable("total")), None, 1])
def test_assignment_requires_variable_identity(target: object) -> None:
    with pytest.raises(RTCValidationError, match="target must be a Variable"):
        VariableAssignment(target, VariableOperator.ASSIGN, 1)  # type: ignore[arg-type]


@pytest.mark.parametrize("operator", list(VariableOperator))
def test_assignments_support_all_operators(operator: VariableOperator) -> None:
    target = Variable("total")
    reference = Reference(target)
    if operator is VariableOperator.ASSIGN:
        assignment = VariableAssignment(target, operator, reference)
    elif operator is VariableOperator.IF:
        assignment = VariableAssignment(target, operator, reference, 1, 2)
    elif operator is VariableOperator.TIMER:
        assignment = VariableAssignment(target, operator, reference)
    else:
        assignment = VariableAssignment(target, operator, reference, 1)
    assert assignment.operator is operator


@pytest.mark.parametrize(
    ("operator", "first", "second", "third", "measurement"),
    [
        ("+", 1, 2, None, None),
        (VariableOperator.ASSIGN, None, None, None, None),
        (VariableOperator.ASSIGN, "total", None, None, None),
        (VariableOperator.ASSIGN, True, None, None, None),
        (VariableOperator.ASSIGN, float("inf"), None, None, None),
        (VariableOperator.ASSIGN, 1e20, None, None, None),
        (VariableOperator.ADD, 1, None, None, None),
        (VariableOperator.ADD, 1, 2, 3, None),
        (VariableOperator.ASSIGN, 1, 2, None, None),
        (VariableOperator.IF, 1, 2, None, None),
        (VariableOperator.TIMER, 1, [], None, None),
        (VariableOperator.TIMER, 1, None, True, None),
        (VariableOperator.ASSIGN, 1, None, None, ""),
        (VariableOperator.ASSIGN, 1, None, None, "12345678"),
        (VariableOperator.ASSIGN, 1, None, None, 123),
    ],
)
def test_assignment_preserves_existing_field_validation(
    operator: object,
    first: object,
    second: object,
    third: object,
    measurement: object,
) -> None:
    with pytest.raises(RTCValidationError):
        VariableAssignment(
            Variable("total"),
            operator,  # type: ignore[arg-type]
            first,  # type: ignore[arg-type]
            second,  # type: ignore[arg-type]
            third,  # type: ignore[arg-type]
            measurement,  # type: ignore[arg-type]
        )


def test_assignment_rejects_name_only_references() -> None:
    with pytest.raises(RTCValidationError, match="argument 1 must be"):
        VariableAssignment(
            Variable("total"),
            VariableOperator.ASSIGN,
            "other",  # type: ignore[arg-type]
        )
