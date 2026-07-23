"""System and service log diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

READ_LOGS_SCHEMA = {
    "name": "read_logs",
    "description": (
        "Read recent system or service logs. Use this to find error "
        "messages, warnings, or crash traces."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "enum": ["service", "dmesg", "syslog"],
                "description": (
                    "Log source: 'service' for journalctl, "
                    "'dmesg' for kernel ring buffer, "
                    "'syslog' for /var/log/syslog"
                ),
            },
            "service_name": {
                "type": "string",
                "description": (
                    "Service name for journalctl "
                    "(required if source is 'service')"
                ),
            },
            "lines": {
                "type": "integer",
                "description": (
                    "Number of recent lines to return (default: 50)"
                ),
                "default": 50,
            },
            "level": {
                "type": "string",
                "enum": ["err", "warning", "info", "all"],
                "description": (
                    "Filter by log level (default: 'all')"
                ),
                "default": "all",
            },
        },
        "required": ["source"],
    },
}


@register_tool(name="read_logs", schema=READ_LOGS_SCHEMA)
async def read_logs(
    ssh_runner: SSHRunner,
    source: str,
    service_name: str | None = None,
    lines: int = 50,
    level: str = "all",
) -> ToolOutput:
    """Read logs from journalctl, dmesg, or syslog."""

    if source == "service":
        if not service_name:
            return ToolOutput(
                tool_name="read_logs",
                stdout="",
                stderr="service_name is required when source='service'",
                exit_code=1,
                allowed=True,
            )
        args = [
            "-u", service_name,
            "-n", str(lines),
            "--no-pager",
        ]
        if level != "all":
            args.extend(["-p", level])
        res = ssh_runner.execute("journalctl", args)

    elif source == "dmesg":
        args = ["--time-format=iso"]
        if level != "all":
            args.extend(["--level", level])
        res = ssh_runner.execute("dmesg", args)

    else:  # syslog
        res = ssh_runner.execute("tail", ["-n", str(lines), "/var/log/syslog"])

    # Truncate to requested line count for dmesg (no native -n flag)
    stdout = res.stdout.strip()
    if source == "dmesg":
        output_lines = stdout.split("\n")
        if len(output_lines) > lines:
            stdout = "\n".join(output_lines[-lines:])

    return ToolOutput(
        tool_name="read_logs",
        stdout=stdout,
        stderr=res.stderr,
        exit_code=res.exit_code,
        duration_ms=res.duration_ms,
        allowed=res.allowed,
    )
