"""TLS certificate inspection diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

CHECK_CERTIFICATES_SCHEMA = {
    "name": "check_certificates",
    "description": (
        "Inspect a TLS certificate served by a host. Checks expiry, "
        "issuer, and subject. Use when TLS/HTTPS failures are suspected."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": (
                    "Hostname to connect to (default: 'localhost')"
                ),
                "default": "localhost",
            },
            "port": {
                "type": "integer",
                "description": "Port to connect to (default: 443)",
                "default": 443,
            },
        },
    },
}


@register_tool(
    name="check_certificates",
    schema=CHECK_CERTIFICATES_SCHEMA,
)
async def check_certificates(
    ssh_runner: SSHRunner,
    host: str = "localhost",
    port: int = 443,
) -> ToolOutput:
    """Execute 'openssl s_client' to inspect a TLS certificate."""

    # openssl s_client -connect host:port -servername host </dev/null
    # We pass the connect string and servername as separate args.
    # The shell redirect (</dev/null) cannot be used directly
    # since our runner blocks shell operators. Instead we rely on
    # the SSH channel closing stdin after command execution, which
    # has the same effect with Paramiko's exec_command.
    res = ssh_runner.execute(
        "openssl",
        [
            "s_client",
            "-connect",
            f"{host}:{port}",
            "-servername",
            host,
        ],
    )

    return ToolOutput(
        tool_name="check_certificates",
        stdout=res.stdout.strip(),
        stderr=res.stderr,
        exit_code=res.exit_code,
        duration_ms=res.duration_ms,
        allowed=res.allowed,
    )
