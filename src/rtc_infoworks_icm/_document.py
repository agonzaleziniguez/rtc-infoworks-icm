"""Ordered object membership, scope, and regulator-section validation."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from rtc_infoworks_icm._validation import (
    validate_nonempty_text,
    validate_single_line_text,
)
from rtc_infoworks_icm.elements.comment import Comment
from rtc_infoworks_icm.elements.controller import Controller
from rtc_infoworks_icm.elements.logic import Logic
from rtc_infoworks_icm.elements.range import Range
from rtc_infoworks_icm.elements.regulator import Regulator
from rtc_infoworks_icm.elements.rule import Rule
from rtc_infoworks_icm.elements.table import Table
from rtc_infoworks_icm.elements.variable import Variable, VariableAssignment
from rtc_infoworks_icm.exceptions import RTCValidationError
from rtc_infoworks_icm.reference import Reference

type ReferenceableElement = Controller | Logic | Range | Table | Variable
type RTCElement = (
    Comment
    | Controller
    | Logic
    | Range
    | Regulator
    | Rule
    | Table
    | Variable
    | VariableAssignment
)


@dataclass(slots=True)
class _RegulatorSection:
    regulator: Regulator
    referenceable_elements_by_name: dict[str, ReferenceableElement] = field(
        default_factory=dict
    )
    contains_rule: bool = False


@dataclass(slots=True)
class DocumentState:
    """Validation facts accumulated while reading the ordered document.

    The name-indexed maps contain only elements that can be referenced; comments,
    assignments, regulators, and rules are validated separately. Global elements
    remain visible in regulator sections, where local elements may shadow them.
    """

    global_referenceable_elements_by_name: dict[str, ReferenceableElement] = field(
        default_factory=dict
    )
    declaration_scope_by_element: dict[ReferenceableElement, Regulator | None] = field(
        default_factory=dict
    )
    initialized_variables: set[Variable] = field(default_factory=set)
    regulator_ids_seen: set[str] = field(default_factory=set)
    current_section: _RegulatorSection | None = None

    def adding(self, elements: Sequence[RTCElement]) -> DocumentState:
        """Validate additions on a copy so failure leaves this state unchanged."""
        candidate = self._copy_for_update()
        for element in elements:
            candidate._record_element(element)
        return candidate

    def _copy_for_update(self) -> DocumentState:
        current_section = self.current_section
        if current_section is not None:
            current_section = _RegulatorSection(
                regulator=current_section.regulator,
                referenceable_elements_by_name=(
                    current_section.referenceable_elements_by_name.copy()
                ),
                contains_rule=current_section.contains_rule,
            )

        return DocumentState(
            global_referenceable_elements_by_name=(
                self.global_referenceable_elements_by_name.copy()
            ),
            declaration_scope_by_element=self.declaration_scope_by_element.copy(),
            initialized_variables=self.initialized_variables.copy(),
            regulator_ids_seen=self.regulator_ids_seen.copy(),
            current_section=current_section,
        )

    def _record_element(self, element: RTCElement) -> None:
        if isinstance(element, Comment):
            return
        if isinstance(element, Regulator):
            self._add_regulator(element)
        elif isinstance(element, Rule):
            self._add_rule(element)
        elif isinstance(element, VariableAssignment):
            self._add_assignment(element)
        else:
            self._add_definition(element)

    def _add_regulator(self, new_regulator: Regulator) -> None:
        """Validate the current section, then begin the newly declared one."""
        if new_regulator.regulator_id in self.regulator_ids_seen:
            raise RTCValidationError(
                f"duplicate regulator ID {new_regulator.regulator_id!r}"
            )

        current_section = self.current_section
        if current_section is not None and not current_section.contains_rule:
            raise RTCValidationError(
                f"regulator {current_section.regulator.regulator_id!r} "
                "requires at least one rule"
            )

        self.regulator_ids_seen.add(new_regulator.regulator_id)
        self.current_section = _RegulatorSection(regulator=new_regulator)

    def _add_rule(self, rule: Rule) -> None:
        if self.current_section is None:
            raise RTCValidationError("rule must belong to a regulator section")
        self._validate_references(rule)
        self.current_section.contains_rule = True

    def _add_definition(self, element: ReferenceableElement) -> None:
        elements_by_name = self._current_referenceable_elements_by_name()
        if element.name in elements_by_name:
            raise RTCValidationError(f"duplicate definition name {element.name!r}")
        if element in self.declaration_scope_by_element:
            raise RTCValidationError("element is already registered in this document")

        self._validate_references(element)
        elements_by_name[element.name] = element
        declaration_scope = (
            self.current_section.regulator if self.current_section is not None else None
        )
        self.declaration_scope_by_element[element] = declaration_scope

    def _add_assignment(self, assignment: VariableAssignment) -> None:
        target = assignment.target
        target_scope = self._require_visible_element(
            target,
            field="variable assignment target",
            initializing_variable=target,
            undeclared_message="assignment target is not registered in this document",
        )
        current_regulator = (
            self.current_section.regulator if self.current_section is not None else None
        )
        if target_scope is not current_regulator:
            raise RTCValidationError(
                "Variable updates must belong to their creation scope"
            )

        self._validate_references(assignment, initializing_variable=target)
        self.initialized_variables.add(target)

    def _validate_references(
        self,
        element: RTCElement,
        *,
        initializing_variable: Variable | None = None,
    ) -> None:
        for field_name, reference in _references(element):
            target = reference.target
            if not isinstance(target, (Controller, Logic, Range, Table, Variable)):
                raise RTCValidationError(f"{field_name} has an unsupported target")
            self._require_visible_element(
                target,
                field=field_name,
                initializing_variable=initializing_variable,
            )

    def _require_visible_element(
        self,
        target: ReferenceableElement,
        *,
        field: str,
        initializing_variable: Variable | None,
        undeclared_message: str | None = None,
    ) -> Regulator | None:
        try:
            declaration_scope = self.declaration_scope_by_element[target]
        except KeyError:
            if undeclared_message is not None:
                raise RTCValidationError(undeclared_message) from None
            raise RTCValidationError(
                f"{field} target {target.name!r} is foreign or not yet declared"
            ) from None

        local = (
            self.current_section.referenceable_elements_by_name.get(target.name)
            if self.current_section is not None
            else None
        )
        visible = (
            local
            if local is not None
            else self.global_referenceable_elements_by_name.get(target.name)
        )
        if visible is not target:
            raise RTCValidationError(
                f"{field} target {target.name!r} is outside "
                "the current scope or shadowed"
            )

        if isinstance(target, Variable):
            if (
                target is not initializing_variable
                and target not in self.initialized_variables
            ):
                raise RTCValidationError(
                    f"{field} Variable {target.name!r} requires its first assignment"
                )

        return declaration_scope

    def _current_referenceable_elements_by_name(
        self,
    ) -> dict[str, ReferenceableElement]:
        if self.current_section is None:
            return self.global_referenceable_elements_by_name
        return self.current_section.referenceable_elements_by_name

    def finish(self) -> None:
        if self.current_section is None:
            raise RTCValidationError("document requires at least one regulator")
        if not self.current_section.contains_rule:
            raise RTCValidationError(
                f"regulator {self.current_section.regulator.regulator_id!r} "
                "requires at least one rule"
            )

    @classmethod
    def validate(cls, elements: Sequence[RTCElement]) -> None:
        state = cls()
        for element in elements:
            state._record_element(element)
        state.finish()


def validate_document(name: str, elements: Sequence[RTCElement]) -> None:
    """Replay incremental rules before the destination is opened."""
    validate_document_name(name)
    DocumentState.validate(elements)


def validate_document_name(name: str) -> None:
    validate_nonempty_text(name, field="document name")
    validate_single_line_text(name, field="document name")


def _references(element: RTCElement) -> Iterator[tuple[str, Reference]]:
    if isinstance(element, Range):
        if isinstance(element.location, Reference):
            yield "variable range location", element.location
    elif isinstance(element, Logic):
        conditions = (
            element.condition_1,
            element.condition_2,
            element.condition_3,
            element.condition_4,
        )
        for position, condition in enumerate(conditions, start=1):
            if condition is not None:
                yield f"logic condition {position}", condition
    elif isinstance(element, Table):
        yield "table input", element.input_range
    elif isinstance(element, VariableAssignment):
        arguments = (
            element.argument_1,
            element.argument_2,
            element.argument_3,
        )
        for position, argument in enumerate(arguments, start=1):
            if isinstance(argument, Reference):
                yield f"variable argument {position}", argument
    elif isinstance(element, Controller):
        if element.sensor is not None:
            yield "controller sensor", element.sensor
    elif isinstance(element, Rule):
        if element.condition is not None:
            yield "rule condition", element.condition
        if element.controller is not None:
            yield "rule controller", element.controller
        if element.variable_value is not None:
            yield "rule variable value", element.variable_value
