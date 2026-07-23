"""Disk and storage diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

CHECK_DISK_USAGE_SCHEMA = {
    "name": "check_disk_usage",
    "description": (
        "Check filesystem disk usage. Use this when disk space issues are "
        "suspected (services failing to write, log rotation issues)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Specific path to check with `du` (optional, defaults to filesystem overview with `df`)",
            }
        },
    },
}


@register_tool(name="check_disk_usage", schema=CHECK_DISK_USAGE_SCHEMA)
async def check_disk_usage(ssh_runner: SSHRunner, path: str | None = None) -> ToolOutput:
    """Execute 'df -h' and optionally 'du -sh' to inspect disk usage."""

    # 1. Base overview: df -h
    df_res = ssh_runner.execute("df", ["-h"])

    combined_stdout = f"--- FILESYSTEM OVERVIEW (df -h) ---\n{df_res.stdout.strip()}"
    combined_stderr = df_res.stderr
    duration_ms = df_res.duration_ms
    exit_code = df_res.exit_code
    allowed = df_res.allowed

    # 2. Specific path check: du -sh (if provided and allowed)
    if path:
        du_res = ssh_runner.execute("du", ["-sh", path])
        combined_stdout += f"\n\n--- DIRECTORY USAGE (du -sh {path}) ---\n{du_res.stdout.strip()}"

        if du_res.stderr:
            combined_stderr += f"\ndu stderr: {du_res.stderr}"

        duration_ms += du_res.duration_ms
        exit_code = max(exit_code, du_res.exit_code)
        allowed = allowed and du_res.allowed

    return ToolOutput(
        tool_name="check_disk_usage",
        stdout=combined_stdout.strip(),
        stderr=combined_stderr.strip(),
        exit_code=exit_code,
        duration_ms=duration_ms,
        allowed=allowed,
    )
