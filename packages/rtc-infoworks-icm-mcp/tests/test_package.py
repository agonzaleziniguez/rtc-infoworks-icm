from importlib.metadata import distribution

import pytest
from rtc_infoworks_icm_mcp.server import main


def test_mcp_package_imports() -> None:
    import rtc_infoworks_icm_mcp

    assert rtc_infoworks_icm_mcp.__all__ == []


def test_mcp_package_identity() -> None:
    package = distribution("rtc-infoworks-icm-mcp")

    assert package.metadata["Name"] == "rtc-infoworks-icm-mcp"
    assert package.requires == ["rtc-infoworks-icm"]
    command = next(
        entry
        for entry in package.entry_points
        if entry.group == "console_scripts" and entry.name == "rtc-infoworks-icm-mcp"
    )
    assert command.value == "rtc_infoworks_icm_mcp.server:main"


def test_mcp_command_reports_unimplemented_server() -> None:
    with pytest.raises(
        SystemExit, match="The rtc-infoworks-icm MCP server is not implemented yet."
    ):
        main()
