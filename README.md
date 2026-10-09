# rtc-infoworks-icm

Build InfoWorks ICM Real Time Control (RTC) text files with Python.

Define ranges, tables, variables, logic, controllers, and regulator rules using
typed Python objects, with validation before export.

Requires **Python 3.14+**, has **no runtime dependencies**, and does not require
ICM to generate files. The library is in early development: validate generated
files in ICM before using them in a modelling workflow.

## Installation

Install from the current `main` branch:

```bash
python -m pip install "git+https://github.com/agonzaleziniguez/rtc-infoworks-icm.git"
```

With uv:

```bash
uv add "rtc-infoworks-icm @ git+https://github.com/agonzaleziniguez/rtc-infoworks-icm.git"
```

For reproducibility, pin the Git URL using `...git@<commit>`.
The distribution is `rtc-infoworks-icm`; the import is `rtc_infoworks_icm`.

## Your first RTC file

This example uses a node's water level to select a regulator position from a
step table. Replace `node.1` and `pump.1` with the appropriate identifiers from
your ICM network, and choose values suitable for your model.

```python
from rtc_infoworks_icm import RTCCreator, RangeType, RuleType, TableType

rtc = RTCCreator("Level control")
rtc.comment("Select a regulator position from the measured water level.")

level = rtc.range_("level", RangeType.LEVEL, location="node.1")
position = rtc.table(
    "position",
    level,
    TableType.STEP,
    rows=[(0, 0.2), (10, 0.8)],
)

rtc.regulator("pump.1")
rtc.rule(RuleType.POSITION, variable_value=position)

rtc.end()
rtc.write("control.rtc")
```

Run with Python or `uv run`, then import `control.rtc` into ICM and check
the definitions against your network.

`end()` closes editing. `write()` requires it, validates the complete document,
and writes UTF-8 text with LF line endings. It **overwrites an existing file**.
Parent directories must already exist; finished documents can be written again.

## Building blocks

| Method | Purpose | Returns |
|---|---|---|
| `comment(text)` | Add descriptive text | `None` |
| `range_(name, type, ...)` | Define a measured, constant, or time-based input | `Range` |
| `table(name, input_range, type, rows, ...)` | Map input values to numeric outputs | `Table` |
| `variable(name, ...)` | Declare a Variable or append an assignment | `Variable` |
| `logic(name, operator, condition_1, ...)` | Combine conditions | `Logic` |
| `controller(name, type, ...)` | Define a controller | `Controller` |
| `regulator(regulator_id)` | Start a regulator's section | `None` |
| `rule(type, ...)` | Add a Rule to the current regulator | `None` |
| `end()` | Close the document for editing | `None` |
| `write(path)` | Validate and write the complete document | `None` |

Use enums from `rtc_infoworks_icm`, such as `RangeType.LEVEL` and `RuleType.POSITION`,
rather than string option codes.

### References are objects

Pass returned objects to other methods, as with `level` and `position` above;
their names are only used in the serialized file. Network locations and regulator
IDs remain strings. Returned objects are immutable; methods do not support
chaining. `Range`, `Table`, `Variable`, `Logic`, and `Controller` are also exported
for type annotations.

## Variables

A Variable is a stable identity, not a Python container holding its calculated
value. Each operation appends a separate assignment for ICM to execute.

```python
from rtc_infoworks_icm import RTCCreator, RuleType, VariableOperator

rtc = RTCCreator("Variable control")
position = rtc.variable("position", VariableOperator.ASSIGN, 0.2)
rtc.variable(position, VariableOperator.ADD, position, 0.1)

rtc.regulator("pump.1")
rtc.rule(RuleType.POSITION, variable_value=position)
rtc.end()
rtc.write("variable-control.rtc")
```

Updates return the same object; use it for subsequent assignments rather than
redeclaring its name. `ADD, position, 0.1` has two explicit operands.

You can reserve an identity without an assignment using `rtc.variable("name")`.
It emits no RTC line until an assignment is added. A first assignment may read its
own Variable, using ICM's initial zero value; other elements may read it only
after its first successful assignment.

The optional `measurement` belongs to an assignment, not the Variable identity.

## Scope and ordering

- Declare objects before referencing them, and use objects from the same creator.
- Referenceable definitions before the first `regulator()` are global.
- Definitions after `regulator()` belong to that regulator's section. Starting
  another regulator starts a new local scope; earlier local definitions are no
  longer available.
- Global definitions remain readable inside regulator sections. Update a
  Variable only in the scope where it was declared.
- Names must be unique across referenceable element types within a scope.
  Different regulator sections may reuse a name.
- A local name shadows a global name. Holding the global object does not bypass
  shadowing: RTC text resolves references by name.
- Regulator IDs must be unique, and every regulator section needs at least one Rule.

## Tables and time inputs

Table rows are `(input, output)` pairs with numeric outputs. Inputs must match
the source type:

- Numbers for numeric bounds and table inputs.
- `datetime.datetime` for calendar-time inputs.
- `datetime.time` for repeating-time inputs.
- `(weekday, datetime.time)` for weekly repeating inputs, with
  `1=Monday` through `7=Sunday`.

## Errors and limitations

Invalid input raises `RTCValidationError`. Additions are checked immediately;
failed operations leave the creator unchanged. `write()` validates the complete
document before opening the destination.

`end()` prevents further editing but does not itself check document completeness.
Filesystem errors from `write()` propagate to the caller.

FUZZY and CENTAUR controller-specific settings are not implemented yet.
The library does not run models, evaluate rules, import existing RTC files, or
check that network identifiers exist in ICM.

## Development

Clone the repository, then run:

```bash
uv sync --all-packages
uv run pytest
uv run basedpyright
uv run ruff check .
uv run ruff format --check .
uv build --package rtc-infoworks-icm
```

The separate [MCP package](packages/rtc-infoworks-icm-mcp/) is a skeleton;
the core has no MCP dependencies.

Report bugs or request features through
[GitHub Issues](https://github.com/agonzaleziniguez/rtc-infoworks-icm/issues).

## License

Licensed under the [MIT License](LICENSE).
