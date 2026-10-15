import anyio
import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent
from rtc_infoworks_icm_mcp.builder import BuildError, validate_definition
from rtc_infoworks_icm_mcp.models import DefinitionInput, Diagnostic


def test_stable_sdk_accepts_nested_contracts_and_exposes_output_schema() -> None:
    server = MCPServer("contract-test")

    @server.tool()
    def inspect_contract(definition: DefinitionInput) -> Diagnostic:
        return Diagnostic(code="incomplete_document", message=definition.name)

    async def exercise() -> None:
        tools = await server.list_tools()
        assert len(tools) == 1
        assert tools[0].input_schema["properties"]
        assert tools[0].output_schema == Diagnostic.model_json_schema()
        payload = {
            "definition": {
                "name": "Control",
                "operations": [
                    {
                        "id": "range",
                        "method": "range_",
                        "name": "level",
                        "type": "Z",
                        "location": "N1",
                    },
                    {
                        "id": "table",
                        "method": "table",
                        "name": "curve",
                        "type": "STEP",
                        "input_range": {"ref": "range"},
                        "rows": [
                            {"input": {"kind": "number", "value": 0}, "output": 0.5}
                        ],
                    },
                ],
            }
        }
        result = await server.call_tool("inspect_contract", payload)
        assert isinstance(result, CallToolResult)
        assert result.is_error is False
        diagnostic = Diagnostic.model_validate(result.structured_content)
        assert diagnostic.message == "Control"
        with pytest.raises(ToolError):
            await server.call_tool(
                "inspect_contract",
                {"definition": {"name": "Control", "operations": [{"method": "eval"}]}},
            )

    anyio.run(exercise)


def test_stable_sdk_preserves_explicit_error_results() -> None:
    server = MCPServer("error-contract-test")

    @server.tool()
    def check_contract(definition: DefinitionInput) -> CallToolResult:
        try:
            validate_definition(definition)
        except BuildError as error:
            return CallToolResult(
                is_error=True,
                content=[
                    TextContent(type="text", text=error.diagnostic.model_dump_json())
                ],
                structured_content=error.diagnostic.model_dump(mode="json"),
            )
        return CallToolResult(content=[TextContent(type="text", text="Complete")])

    async def exercise() -> None:
        result = await server.call_tool(
            "check_contract", {"definition": {"name": "Control", "operations": []}}
        )
        assert isinstance(result, CallToolResult)
        assert result.is_error is True
        diagnostic = Diagnostic.model_validate(result.structured_content)
        assert diagnostic.code == "incomplete_document"

    anyio.run(exercise)
