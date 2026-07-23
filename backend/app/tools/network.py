"""Network interface and routing diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

# ---------------------------------------------------------------------------
# check_network_interfaces
# ---------------------------------------------------------------------------

CHECK_NETWORK_INTERFACES_SCHEMA = {
    "name": "check_network_interfaces",
    "description": (
        "List network interfaces with their state (UP/DOWN), IP addresses, "
        "and MAC addresses. Use this when connectivity issues or interface "
        "problems are suspected."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


@register_tool(
    name="check_network_interfaces",
    schema=CHECK_NETWORK_INTERFACES_SCHEMA,
)
async def check_network_interfaces(
    ssh_runner: SSHRunner,
) -> ToolOutput:
    """Execute 'ip addr show' to inspect network interfaces."""

    res = ssh_runner.execute("ip", ["addr", "show"])

    return ToolOutput(
        tool_name="check_network_interfaces",
        stdout=res.stdout.strip(),
        stderr=res.stderr,
        exit_code=res.exit_code,
        duration_ms=res.duration_ms,
        allowed=res.allowed,
    )


# ---------------------------------------------------------------------------
# check_routes
# ---------------------------------------------------------------------------

CHECK_ROUTES_SCHEMA = {
    "name": "check_routes",
    "description": (
        "Show the system routing table including default gateway. "
        "Use this when traffic is not reaching its destination or "
        "routing is misconfigured."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


@register_tool(name="check_routes", schema=CHECK_ROUTES_SCHEMA)
async def check_routes(ssh_runner: SSHRunner) -> ToolOutput:
    """Execute 'ip route show' to inspect the routing table."""

    res = ssh_runner.execute("ip", ["route", "show"])

    return ToolOutput(
        tool_name="check_routes",
        stdout=res.stdout.strip(),
        stderr=res.stderr,
        exit_code=res.exit_code,
        duration_ms=res.duration_ms,
        allowed=res.allowed,
    )
