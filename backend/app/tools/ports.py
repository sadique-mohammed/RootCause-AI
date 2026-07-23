"""Port and socket diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

CHECK_LISTENING_PORTS_SCHEMA = {
    "name": "check_listening_ports",
    "description": (
        "List all TCP/UDP ports with listening processes. Use this to "
        "identify port conflicts or verify a service is actually listening."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "protocol": {
                "type": "string",
                "enum": ["tcp", "udp", "all"],
                "description": "Filter by protocol (default: 'all')",
                "default": "all",
            },
        },
    },
}


@register_tool(
    name="check_listening_ports",
    schema=CHECK_LISTENING_PORTS_SCHEMA,
)
async def check_listening_ports(
    ssh_runner: SSHRunner,
    protocol: str = "all",
) -> ToolOutput:
    """Execute 'ss' to list listening sockets by protocol."""

    # Build args based on protocol filter
    # -l = listening, -n = numeric, -p = show process
    if protocol == "tcp":
        args = ["-tlnp"]
    elif protocol == "udp":
        args = ["-ulnp"]
    else:
        args = ["-tulnp"]

    res = ssh_runner.execute("ss", args)

    return ToolOutput(
        tool_name="check_listening_ports",
        stdout=res.stdout.strip(),
        stderr=res.stderr,
        exit_code=res.exit_code,
        duration_ms=res.duration_ms,
        allowed=res.allowed,
    )
