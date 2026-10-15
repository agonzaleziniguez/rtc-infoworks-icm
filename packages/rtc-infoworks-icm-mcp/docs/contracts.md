# Working control definition contracts

These are the construction contracts, not a running MCP tool catalog. The stdio
server and in-memory editing service are not implemented yet.

## Audience and documentation

This guide is for developers maintaining the MCP adapter. It describes the
implemented operation/edit models, diagnostics, and library-backed builder.
The edit models define requests only; the editing service comes later.

The assistant-facing resources serve a different purpose:

- [Workflow guide](../src/rtc_infoworks_icm_mcp/resources/workflow.md):
  objective clarification, strategy review, responsibilities, and output choices.
- [Element guide](../src/rtc_infoworks_icm_mcp/resources/elements.md):
  supported building blocks, composition rules, and limitations.

These guides will be exposed to the assistant by the server; end users should
not need to read them. The
[repository README](../../../README.md#mcp-server-in-development) is the user
entry point.

The adapter uses the official MCP Python SDK and Pydantic, declared in its
package metadata and locked in the workspace lockfile. The core remains
dependency-free. SDK compatibility tests cover nested schemas, structured
outputs, and explicit error results.

## One ordered definition

A definition contains a document name and an ordered `operations` array.
Each operation explicitly identifies the public library call and its arguments.
The builder executes this sequence using a fresh `RTCCreator`; it never edits RTC
text or executes Python supplied by a client.

```json
{
  "name": "Level response",
  "operations": [
    {
      "id": "level",
      "method": "range_",
      "name": "level",
      "type": "Z",
      "location": "N1"
    },
    {
      "id": "position",
      "method": "table",
      "name": "position",
      "type": "STEP",
      "input_range": {"ref": "level"},
      "rows": [
        {"input": {"kind": "number", "value": 0}, "output": 0.2},
        {"input": {"kind": "number", "value": 10}, "output": 0.8}
      ]
    },
    {"id": "weir", "method": "regulator", "regulator_id": "W1"},
    {
      "id": "position_rule",
      "method": "rule",
      "type": "POS",
      "variable_value": {"ref": "position"}
    }
  ]
}
```

This illustrates construction, not a suitable strategy for a particular model.
Measurements, operating limits and desired behaviour must be clarified first.

## IDs, names, and references

- Operation IDs start with an ASCII letter, followed by ASCII letters, digits,
  underscores or hyphens. They are unique across the entire definition.
- An RTC `name` is distinct from its operation ID and follows library limits.
  The library permits at most ten characters and rejects CR/LF in names.
- `location` strings and `regulator_id` are network identifiers, not references.
- References use `{"ref": "operation-id"}`. Bare reference-name strings are not
  accepted. They must identify an earlier referenceable operation.
- Ranges, tables, variable declarations, logic, and controllers produce objects.
  Comments, assignments, regulators, and rules cannot be reference targets.
- A known ID does not bypass scope, initialization, or shadowing checks.

## Operations

Field names follow the public library. Unknown fields and methods are errors.
Use serialized enum values, not Python enum names: `"Z"`, not `"LEVEL"`; `"+"`,
not `"ADD"`. Values come directly from the library enums in the JSON schemas.

| `method` | Required fields beyond `id` | Optional fields / defaults |
|---|---|---|
| `comment` | `text` | None |
| `range_` | `name`, `type` | `location`, `minimum`, `maximum`: null; `distance`: 0 |
| `table` | `name`, `input_range`, `type`, `rows` | `output_measurement`: null |
| `declare_variable` | `name` | None |
| `assign_variable` | `target`, `operator`, `argument_1` | `argument_2`, `argument_3`, `measurement`: null |
| `logic` | `name`, `operator`, `condition_1` | `condition_2` through `condition_4`: null |
| `controller` | `name`, `type`, `measurement_interval` | `sensor`: null; `filter_coefficient`, `proportional`, `integral`, `differential`: 0 |
| `regulator` | `regulator_id` | `initial`, `threshold`, `positive_rate`, `negative_rate`: null; `override_other_control`: false |
| `rule` | `type` | `condition`, `controller`, `variable_value`: null; `fixed_value`: 0 |

Required wire fields do not describe all semantic requirements: the library
checks operator arity, valid source types, location requirements, controller
constraints, and unused fields. Explicit null has the same meaning as an omitted
nullable field. Null is not accepted for non-nullable fields.

Variable declaration calls `rtc.variable(name)` and does not emit a line.
Assignment calls `rtc.variable(existing_object, operator, ...)` and preserves
the identity. Its operands are numbers or explicit references:

```json
{
  "name": "Variable example",
  "operations": [
    {"id": "total", "method": "declare_variable", "name": "total"},
    {
      "id": "increment",
      "method": "assign_variable",
      "target": {"ref": "total"},
      "operator": "+",
      "argument_1": {"ref": "total"},
      "argument_2": 1
    }
  ]
}
```

The first assignment can read its own Variable. Other elements require its
first successful assignment. This example is constructible but incomplete:
it has no regulator or rule.

## Numbers and temporal inputs

JSON numbers are accepted without string/boolean coercion. NaN and infinity are
rejected even if a decoder accepts those non-standard JSON literals.
Integer-only fields reject floating-point inputs. The library's numeric field
widths, rounding, and regulator truncation still apply; successful construction
does not mean all submitted decimal precision is preserved in RTC text.

Range bounds and table inputs are explicitly tagged:

```json
[
  {"kind": "number", "value": 1.5},
  {"kind": "datetime", "value": "2026-01-01T12:00:00"},
  {"kind": "time", "value": "12:00:00"},
  {"kind": "weekly_time", "weekday": 1, "value": "12:00:00"}
]
```

- Calendar format: `YYYY-MM-DDTHH:MM:SS`, valid dates, years 1000-9999.
  Earlier years are excluded because the core's platform date formatter does
  not guarantee four-digit years for them.
- Clock format: `HH:MM:SS`, from `00:00:00` through `23:59:59`.
- Weekly weekdays: integers 1 (Monday) through 7 (Sunday).
- No timezone, fractional seconds, fold flag, implicit midnight normalization,
  locale parsing, or conversion from a plain string.
- Table rows are objects with `input` and numeric `output`, not arbitrary pairs.
  Input category, ordering, and bounds must satisfy the library.

## Edits: contract only in this step

```json
{
  "definition_id": "control",
  "expected_revision": 0,
  "edits": [
    {
      "action": "insert",
      "before": "position_rule",
      "operation": {"id": "note", "method": "comment", "text": "Review"}
    },
    {
      "action": "replace",
      "target": "note",
      "operation": {"id": "note", "method": "comment", "text": "Updated"}
    },
    {"action": "remove", "target": "note"}
  ]
}
```

Revision is a nonnegative integer. At least one edit is required. Insertion
without `before` appends. The upcoming service will preserve IDs on replacement,
reject unknown targets/stale revisions, and accept a group only if the entire
candidate constructs successfully. It will never reorder operations or
automatically delete dependents. Those application rules are not implemented by
the edit schema alone.

## Checks and errors

`parse_definition()` / `parse_edits()` decode strict JSON. Malformed requests
raise `RequestError` with `invalid_request` diagnostics and structured validation
paths. Diagnostics omit raw input objects; validation messages and field paths
are retained.

`build_definition()` returns an open creator or raises `BuildError`. It permits
an incomplete working definition, but does not bypass incremental validation.
`validate_definition()` additionally checks completeness. Rendering requires
completeness and uses the core's public `render()` method.

Diagnostics contain `code`, `message`, and nullable `operation_id`,
`operation_index`, and `field`. Indexes are zero-based. Library messages are
preserved, not parsed to manufacture field locations.

| Code | Meaning |
|---|---|
| `invalid_request` | Incorrect JSON, input shape, scalar type, enum or temporal value |
| `duplicate_operation_id` | An operation ID is reused |
| `unknown_reference` | ID is missing, forward, or does not produce an object |
| `wrong_reference_kind` | Object is not an accepted kind for this argument |
| `invalid_document` | The library rejected the name or an operation |
| `incomplete_document` | Construction succeeded, but whole-document validation failed |

The future MCP boundary must report failures as `isError` tool responses, not
successes containing hidden error fields. The stable SDK's nested schemas,
structured outputs, and explicit error results are covered by compatibility
tests, but no production MCP tools are registered yet.

## Developer entry points

```python
from rtc_infoworks_icm_mcp.builder import build_definition, validate_definition
from rtc_infoworks_icm_mcp.models import parse_definition

definition = parse_definition(
    '{"name":"Example","operations":['
    '{"id":"reg","method":"regulator","regulator_id":"W1"},'
    '{"id":"rule","method":"rule","type":"POS"}]}'
)
validate_definition(definition)
rtc_text = build_definition(definition).render()
```

The generated schema snapshot is
[`contracts.schema.json`](../tests/contracts.schema.json). Changes to it must be
reviewed along with models, documentation, and SDK compatibility tests.
