"""Memory and swap diagnostic tools."""

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

CHECK_MEMORY_SCHEMA = {
    "name": "check_memory",
    "description": (
        "Check system memory usage including RAM and swap. Use this when "
        "OOM kills, memory leaks, or swap thrashing are suspected."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


@register_tool(name="check_memory", schema=CHECK_MEMORY_SCHEMA)
async def check_memory(ssh_runner: SSHRunner) -> ToolOutput:
    """Execute 'free -m' and read '/proc/meminfo' to inspect memory usage."""

    # 1. Base overview: free -m
    free_res = ssh_runner.execute("free", ["-m"])

    # 2. Detailed info: /proc/meminfo
    meminfo_res = ssh_runner.execute("cat", ["/proc/meminfo"])

    # Truncate meminfo to top 15 lines as that contains the most relevant info
    meminfo_lines = meminfo_res.stdout.strip().split("\n")
    limited_meminfo = (
        "\n".join(meminfo_lines[:15]) if len(meminfo_lines) > 15 else meminfo_res.stdout.strip()
    )

    combined_stdout = (
        f"--- MEMORY OVERVIEW (free -m) ---\n{free_res.stdout.strip()}\n\n"
        f"--- DETAILED STATS (top of /proc/meminfo) ---\n{limited_meminfo}"
    )

    combined_stderr = ""
    if free_res.stderr:
        combined_stderr += f"free stderr: {free_res.stderr}\n"
    if meminfo_res.stderr:
        combined_stderr += f"cat stderr: {meminfo_res.stderr}\n"

    duration_ms = free_res.duration_ms + meminfo_res.duration_ms
    exit_code = max(free_res.exit_code, meminfo_res.exit_code)
    allowed = free_res.allowed and meminfo_res.allowed

    return ToolOutput(
        tool_name="check_memory",
        stdout=combined_stdout.strip(),
        stderr=combined_stderr.strip(),
        exit_code=exit_code,
        duration_ms=duration_ms,
        allowed=allowed,
    )
