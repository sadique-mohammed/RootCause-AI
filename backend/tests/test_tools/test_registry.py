"""Unit tests for the central tool registry."""

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import (
    TOOL_REGISTRY,
    ToolOutput,
    execute_tool,
    get_all_tool_schemas,
    register_tool,
)

# Test schema
DUMMY_SCHEMA = {
    "name": "dummy_tool",
    "description": "A dummy tool for testing.",
    "parameters": {"type": "object", "properties": {}},
}


@pytest.fixture(autouse=True)
def clean_registry() -> Generator[None, None, None]:
    """Clear registry before and after tests."""
    # Backup original registry
    original = dict(TOOL_REGISTRY)
    yield
    # Restore original registry
    TOOL_REGISTRY.clear()
    TOOL_REGISTRY.update(original)


@register_tool(name="dummy_tool", schema=DUMMY_SCHEMA)
async def dummy_tool(ssh_runner: SSHRunner, param1: str = "default") -> ToolOutput:
    """A dummy tool implementation."""
    return ToolOutput(
        tool_name="dummy_tool",
        stdout=f"dummy output: {param1}",
        stderr="",
        exit_code=0,
        duration_ms=10,
        allowed=True,
    )


def test_tool_registration() -> None:
    """Test that tools are correctly registered in TOOL_REGISTRY."""
    assert "dummy_tool" in TOOL_REGISTRY
    assert TOOL_REGISTRY["dummy_tool"].name == "dummy_tool"
    assert TOOL_REGISTRY["dummy_tool"].schema == DUMMY_SCHEMA


def test_get_all_tool_schemas() -> None:
    """Test retrieving all tool schemas for LLM registration."""
    schemas = get_all_tool_schemas()
    assert DUMMY_SCHEMA in schemas


@pytest.mark.asyncio
async def test_execute_registered_tool() -> None:
    """Test executing a successfully registered tool."""
    mock_runner = MagicMock(spec=SSHRunner)

    # Execute with explicit param
    output = await execute_tool("dummy_tool", {"param1": "custom"}, mock_runner)
    assert output.tool_name == "dummy_tool"
    assert output.stdout == "dummy output: custom"
    assert output.exit_code == 0
    assert output.allowed is True


@pytest.mark.asyncio
async def test_execute_unregistered_tool() -> None:
    """Test executing a tool that does not exist in the registry."""
    mock_runner = MagicMock(spec=SSHRunner)
    output = await execute_tool("nonexistent_tool", {}, mock_runner)

    assert output.tool_name == "nonexistent_tool"
    assert output.stdout == ""
    assert "not found in registry" in output.stderr
    assert output.exit_code == -1
    assert output.allowed is False
