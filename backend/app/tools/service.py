"""Service and systemd diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

CHECK_SERVICE_STATUS_SCHEMA = {
    "name": "check_service_status",
    "description": (
        "Check the status of a systemd service unit and its recent logs. "
        "Use this when a service is reported as down or misbehaving."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "service_name": {
                "type": "string",
                "description": "Name of the systemd service (e.g., 'nginx', 'sshd', 'postgresql')",
            },
            "log_lines": {
                "type": "integer",
                "description": "Number of recent journal lines to include (default: 30)",
                "default": 30,
            },
        },
        "required": ["service_name"],
    },
}


@register_tool(name="check_service_status", schema=CHECK_SERVICE_STATUS_SCHEMA)
async def check_service_status(ssh_runner: SSHRunner, service_name: str, log_lines: int = 30) -> ToolOutput:
    """Execute 'systemctl status' and 'journalctl' to inspect a service."""

    # 1. Get service status
    status_res = ssh_runner.execute("systemctl", ["status", service_name, "--no-pager"])

    # 2. Get recent logs
    journal_res = ssh_runner.execute("journalctl", ["-u", service_name, "-n", str(log_lines), "--no-pager"])

    # Combine outputs
    combined_stdout = (
        f"--- SYSTEMCTL STATUS ---\n{status_res.stdout.strip()}\n\n"
        f"--- RECENT JOURNAL LOGS ---\n{journal_res.stdout.strip()}"
    )

    combined_stderr = ""
    if status_res.stderr:
        combined_stderr += f"systemctl stderr: {status_res.stderr}\n"
    if journal_res.stderr:
        combined_stderr += f"journalctl stderr: {journal_res.stderr}\n"

    duration_ms = status_res.duration_ms + journal_res.duration_ms
    exit_code = max(status_res.exit_code, journal_res.exit_code)
    allowed = status_res.allowed and journal_res.allowed

    return ToolOutput(
        tool_name="check_service_status",
        stdout=combined_stdout.strip(),
        stderr=combined_stderr.strip(),
        exit_code=exit_code,
        duration_ms=duration_ms,
        allowed=allowed,
    )
