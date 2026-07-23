"""DNS resolution diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

CHECK_DNS_SCHEMA = {
    "name": "check_dns",
    "description": (
        "Test DNS resolution for a domain. Also reads /etc/resolv.conf "
        "to check nameserver configuration. Use when DNS failures are "
        "suspected."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": (
                    "Domain name to resolve (default: 'google.com')"
                ),
                "default": "google.com",
            },
        },
    },
}


@register_tool(name="check_dns", schema=CHECK_DNS_SCHEMA)
async def check_dns(
    ssh_runner: SSHRunner,
    domain: str = "google.com",
) -> ToolOutput:
    """Execute 'dig' and read '/etc/resolv.conf' for DNS diagnostics."""

    # 1. DNS resolution via dig
    dig_res = ssh_runner.execute("dig", [domain, "+short"])

    # 2. Nameserver configuration
    resolv_res = ssh_runner.execute("cat", ["/etc/resolv.conf"])

    combined_stdout = (
        f"--- DIG {domain} +short ---\n"
        f"{dig_res.stdout.strip()}\n\n"
        f"--- /etc/resolv.conf ---\n"
        f"{resolv_res.stdout.strip()}"
    )

    combined_stderr = ""
    if dig_res.stderr:
        combined_stderr += f"dig stderr: {dig_res.stderr}\n"
    if resolv_res.stderr:
        combined_stderr += f"cat stderr: {resolv_res.stderr}\n"

    duration_ms = dig_res.duration_ms + resolv_res.duration_ms
    exit_code = max(dig_res.exit_code, resolv_res.exit_code)
    allowed = dig_res.allowed and resolv_res.allowed

    return ToolOutput(
        tool_name="check_dns",
        stdout=combined_stdout.strip(),
        stderr=combined_stderr.strip(),
        exit_code=exit_code,
        duration_ms=duration_ms,
        allowed=allowed,
    )
