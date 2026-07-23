"""Network connectivity diagnostic tools (ping / traceroute)."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

CHECK_CONNECTIVITY_SCHEMA = {
    "name": "check_connectivity",
    "description": (
        "Test basic network connectivity to a host using ping or "
        "traceroute. Use to verify if the network path is working."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Host or IP to test connectivity to",
            },
            "method": {
                "type": "string",
                "enum": ["ping", "traceroute"],
                "description": "Test method (default: 'ping')",
                "default": "ping",
            },
            "count": {
                "type": "integer",
                "description": (
                    "Number of ping packets "
                    "(default: 4, ignored for traceroute)"
                ),
                "default": 4,
            },
        },
        "required": ["target"],
    },
}


@register_tool(
    name="check_connectivity",
    schema=CHECK_CONNECTIVITY_SCHEMA,
)
async def check_connectivity(
    ssh_runner: SSHRunner,
    target: str,
    method: str = "ping",
    count: int = 4,
) -> ToolOutput:
    """Execute ping or traceroute to test network reachability."""

    if method == "traceroute":
        res = ssh_runner.execute("traceroute", ["-m", "15", target])
    else:
        res = ssh_runner.execute(
            "ping", ["-c", str(count), "-W", "3", target]
        )

    return ToolOutput(
        tool_name="check_connectivity",
        stdout=res.stdout.strip(),
        stderr=res.stderr,
        exit_code=res.exit_code,
        duration_ms=res.duration_ms,
        allowed=res.allowed,
    )
