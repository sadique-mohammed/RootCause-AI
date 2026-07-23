"""Central tool registry and output schemas for diagnostic tools."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from backend.app.core.ssh_runner import SSHRunner


class ToolOutput(BaseModel):
    """Standardized output wrapper for all diagnostic tools."""
    tool_name: str = Field(description="Name of the tool that generated this output")
    stdout: str = Field(description="Raw standard output from the target (truncated to prevent context blowout)")
    stderr: str = Field(default="", description="Raw standard error, if any")
    exit_code: int = Field(default=0, description="Highest exit code encountered during tool execution")
    duration_ms: int = Field(default=0, description="Total execution duration across all wrapped commands")
    allowed: bool = Field(default=True, description="Whether all commands passed the allowlist")

@dataclass
class ToolDefinition:
    """Definition of an LLM-accessible diagnostic tool."""
    name: str
    func: Callable[..., Awaitable[ToolOutput]]
    schema: dict[str, Any]

TOOL_REGISTRY: dict[str, ToolDefinition] = {}

def register_tool(
    name: str, schema: dict[str, Any]
) -> Callable[[Callable[..., Awaitable[ToolOutput]]], Callable[..., Awaitable[ToolOutput]]]:
    """Decorator to register a diagnostic tool with its OpenAI function schema."""
    def decorator(func: Callable[..., Awaitable[ToolOutput]]) -> Callable[..., Awaitable[ToolOutput]]:
        TOOL_REGISTRY[name] = ToolDefinition(name=name, func=func, schema=schema)
        return func
    return decorator

def get_all_tool_schemas() -> list[dict[str, Any]]:
    """Return all tool schemas for LLM function calling registration."""
    return [tool.schema for tool in TOOL_REGISTRY.values()]

async def execute_tool(name: str, args: dict[str, Any], ssh_runner: SSHRunner) -> ToolOutput:
    """Look up and execute a registered tool by name using the provided arguments."""
    if name not in TOOL_REGISTRY:
        return ToolOutput(
            tool_name=name,
            stdout="",
            stderr=f"Tool '{name}' not found in registry.",
            exit_code=-1,
            allowed=False
        )

    tool = TOOL_REGISTRY[name]
    try:
        return await tool.func(ssh_runner=ssh_runner, **args)
    except Exception as err:
        return ToolOutput(
            tool_name=name,
            stdout="",
            stderr=f"Exception executing tool '{name}': {err}",
            exit_code=-1,
            allowed=False
        )
