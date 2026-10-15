# Supported RTC building blocks

This is guidance for the current library-backed construction contracts.
Production MCP tools are not yet available. The schemas define the exact fields
and enum values; this guide explains how to choose and connect operations.

Use this guidance after clarifying and reviewing the control strategy with the
user. Never choose thresholds, network relationships, tuning, or operating limits
just to make a document pass validation.

## Operations and library calls

| Operation | Core method | Role |
|---|---|---|
| `comment` | `comment()` | Describe the implementation |
| `range_` | `range_()` | Define a measured, numeric, or temporal input |
| `table` | `table()` | Map an input to numeric output |
| `declare_variable` | `variable(name)` | Reserve a stable numeric identity |
| `assign_variable` | `variable(object, operator, ...)` | Append an assignment to that identity |
| `logic` | `logic()` | Combine Range/Logic conditions |
| `controller` | `controller()` | Define a supported controller |
| `regulator` | `regulator()` | Begin a section for a network regulator |
| `rule` | `rule()` | Add a rule to the current section |

An operation's ID identifies it for references and future edits. Its RTC name is
the serialized name; a network location is a separate network identifier.
Reference objects with `{"ref":"operation-id"}`, not names or Python expressions.

## Composition rules

- Submit operations in the intended execution order. Define before use.
- Referenceable definitions before the first regulator are global; subsequent
  definitions belong to the current regulator section.
- A new regulator begins a new local scope. Earlier local objects are no longer
  visible. Global objects remain visible unless a local name shadows them.
- Names are unique across referenceable kinds in each scope. IDs are unique
  across the entire working definition.
- Each regulator needs at least one rule before the next regulator or output.
- Holding an explicit global ID does not bypass name shadowing in RTC.

The server never sorts definitions or rules to fix an error. Rule order must be
chosen deliberately; validation alone does not prove the chosen behaviour.

## Reference kinds

- Variable operands and `VAR` range locations: Range, Table, Variable, or Logic.
- Table source and rule variable value: Range, Table, or Variable.
- Logic and rule conditions: Range or Logic.
- Controller sensor: Range, with the core's PID/type restrictions.
- Rule controller: Controller.
- Variable assignment target: a Variable declaration, not a prior assignment ID.

## Variables and time

Declaration emits no RTC line and performs no automatic assignment. The first
assignment may read its own Variable. Other elements can read it only after
that assignment. Update it only within its declaration scope.

Operators use explicit operands: addition needs two, and IF needs three.
Assignment measurement describes that record, not a mutable property of the
identity. The library does not calculate simulation values.

Temporal ranges/tables use tagged calendar, daily-clock, or weekly-clock
inputs with whole-second precision and no timezone. Calendar ordering is based
on wall-clock values, independent of the host timezone. Tables always produce
numeric outputs, even when their inputs are temporal.

## Limitations and review

FUZZY/CENTAUR enum values do not imply that their controller-specific settings
are implemented. Those settings are unsupported; do not invent fields or imply
such a strategy has been fully configured.

Numeric RTC formatting can round values; regulator fields can truncate them.
Review generated values and their suitability for the intended control.

The library does not inspect the network, evaluate rules, tune controllers,
simulate hydraulics, or import existing RTC files. A document can be properly
formatted and valid without achieving its intended model objective.

If an error exposes uncertainty about the intended strategy, ask the user.
Do not silently substitute a different control approach.
