# rtc-infoworks-icm-mcp

An MCP server under development for translating real-time control objectives
into library-built RTC files and reproducible Python scripts.

## Intended workflow

Users describe the modelling problem, not the RTC elements. The assistant asks
for clarification whenever the objective or operating constraints are unclear,
then explains the proposed control behaviour for the user to review.

The assistant expresses the agreed strategy as explicit, ordered library
operations. The server will keep this working control definition in memory,
check proposed edits through the library, and generate the requested outputs:
the Python script, the RTC file, or both.

See the [workflow guide](src/rtc_infoworks_icm_mcp/resources/workflow.md) for the
responsibilities, clarification policy, and planned editing/export behaviour.

## Implementation status

The core library provides non-mutating completeness checks with
`RTCCreator.validate()` and in-memory RTC previews with `RTCCreator.render()`.
Both use the same validation and formatting as file generation.

This MCP package still contains only an importable package and a placeholder
command. There is no working MCP transport, tool catalog, document editing,
Python-script generation, or export service yet.

The planned server will use local stdio and the official MCP Python SDK.
Its code, tests, documentation, and installed runtime will be self-contained.
MCP dependencies will remain separate from the dependency-free core library.

## Validation boundary

A valid RTC file is not proof that a control strategy achieves its hydraulic
objective. Network identifiers, imported settings, and model behaviour must be
checked in InfoWorks ICM.
