# rtc-infoworks-icm

Pure-Python library for building InfoWorks ICM Real Time Control files.

Requires Python 3.14 or newer. Install with `pip install rtc-infoworks-icm` (or `uv add rtc-infoworks-icm`).
The core library has no runtime dependencies.

## Build a control file

```python
from rtc_infoworks_icm import RTCCreator, RangeType, RuleType, TableType

rtc = RTCCreator("Control")
level = rtc.range_("level", RangeType.LEVEL, location="node.1")
curve = rtc.table("curve", level, TableType.STEP, [(0, 0.2), (10, 0.8)])

rtc.regulator("pump.1")
rtc.rule(RuleType.POSITION, variable_value=curve)
rtc.end()
rtc.write("control.rtc")
```

`range_`, `table`, `logic`, `controller`, and `variable` return immutable objects.
Pass these objects as references, not their names. Network locations and regulator
IDs remain strings. `comment`, `regulator`, `rule`, and `end` return `None`.
The five returned model classes are also exported for type annotations.

## Variables: identity versus assignment

```python
from rtc_infoworks_icm import RTCCreator, RuleType, VariableOperator

rtc = RTCCreator("Total")
total = rtc.variable("total")  # Reserve an identity; emit no RTC line.
total = rtc.variable(total, VariableOperator.ADD, total, 100)
rtc.variable(total, VariableOperator.MULTIPLY, total, 2, measurement="m")
initial = rtc.variable("initial", VariableOperator.ASSIGN, 100)

rtc.regulator("pump.1")
rtc.rule(RuleType.POSITION, variable_value=total)
rtc.end()
rtc.write("total.rtc")
```

Updating a Variable returns the **same object** and appends an assignment record.
The object does not hold an evaluated simulation value. Operands are explicit:
`ADD, total, 100` adds 100 to total; `ADD, 100` is incomplete. Measurement belongs
to each assignment, not to the identity.

A first assignment may read its own Variable (ICM initializes it to zero).
Other records require its first successful assignment. An unused identity emits
nothing, and reserving it does not generate an automatic zero assignment.

## Scope and validation

- Objects must come from the same creator and be declared before use.
- Definitions before the first regulator are global. Later definitions belong
  to the current regulator only; locals do not carry into the next section.
- A local name hides a global name. Holding the global object does not bypass
  shadowing, because the generated RTC text resolves references by name.
- Names share a conservative, unique namespace within each scope. Use the same
  Variable object for updates; creating another with the same name is an error.
- Update Variables only in their creation scope. Global Variables can still be
  read inside regulator sections.
- Table rows must match the source's numeric, calendar, or repeating-time input.
  A Table's output is numeric even if its own input is temporal. Weekly inputs
  use `(weekday, time)` pairs, with 1=Monday through 7=Sunday.
- Regulator IDs are unique, and every section requires at least one rule.

Invalid additions raise `RTCValidationError` immediately without reserving names,
appending records, or changing scope. `write` also validates the whole document
before opening the destination, requires `end`, and can be called repeatedly.
Output uses UTF-8 and LF line endings. Filesystem errors propagate to the caller.
FUZZY and CENTAUR controller-specific settings are not implemented yet.

## Migrating from the name-based API

This is a deliberate breaking change: replace reference-name strings with
returned objects, remove fluent chaining, and replace repeated same-name Variable
creation with updates to its identity. Invalid references and incompatible Tables
now fail when added instead of waiting for `write`.

The future MCP application will map external identifiers to these objects.
The core library does not parse JSON or require MCP dependencies.
