"""Process inspection diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

CHECK_PROCESSES_SCHEMA = {
    "name": "check_processes",
    "description": (
        "List running processes sorted by resource usage. Use this to identify "
        "runaway processes, memory hogs, or CPU spinners."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sort_by": {
                "type": "string",
                "enum": ["cpu", "memory"],
                "description": "Sort processes by CPU or memory usage (descending)",
            },
            "limit": {
                "type": "integer",
                "description": "Number of top processes to return (default: 10)",
                "default": 10,
            },
        },
        "required": ["sort_by"],
    },
}


@register_tool(name="check_processes", schema=CHECK_PROCESSES_SCHEMA)
async def check_processes(ssh_runner: SSHRunner, sort_by: str, limit: int = 10) -> ToolOutput:
    """Execute 'ps aux' sorted by the requested resource."""
    sort_flag = "--sort=-%cpu" if sort_by == "cpu" else "--sort=-%mem"

    # Because `head -n` involves a pipe which is blocked by shell injection prevention,
    # we will just run the ps command and do truncation in python, OR
    # we can just run ps aux and accept we'll get the full output up to the 2k char limit.
    # Actually, we can use `top -b -n 1` or `ps aux`.
    # `ps aux` is allowed by allowlist. We'll truncate lines here in the wrapper.

    res = ssh_runner.execute("ps", ["aux", sort_flag])

    if not res.allowed or res.exit_code != 0:
        return ToolOutput(
            tool_name="check_processes",
            stdout=res.stdout,
            stderr=res.stderr,
            exit_code=res.exit_code,
            duration_ms=res.duration_ms,
            allowed=res.allowed,
        )

    # Process limit manually since shell pipes are blocked by security allowlist
    lines = res.stdout.strip().split("\n")
    limited_stdout = (
        "\n".join(lines[: limit + 1]) if len(lines) > limit + 1 else res.stdout.strip()
    )

    return ToolOutput(
        tool_name="check_processes",
        stdout=limited_stdout,
        stderr=res.stderr,
        exit_code=res.exit_code,
        duration_ms=res.duration_ms,
        allowed=res.allowed,
    )
