"""Edge-case and error-path tests across Phases 1-2.2."""

from unittest.mock import MagicMock

import pytest

from backend.app.core.allowlist import validate_command
from backend.app.core.ssh_runner import CommandResult, SSHRunner
from backend.app.tools.connectivity import check_connectivity
from backend.app.tools.disk import check_disk_usage
from backend.app.tools.dns import check_dns
from backend.app.tools.logs import read_logs
from backend.app.tools.memory import check_memory
from backend.app.tools.process import check_processes
from backend.app.tools.registry import execute_tool
from backend.app.tools.service import check_service_status


@pytest.fixture
def mock_ssh() -> MagicMock:
    """Provide a mock SSHRunner."""
    return MagicMock(spec=SSHRunner)


# ── Allowlist edge cases ────────────────────────────────────────────


def test_tail_is_allowed_for_var_log() -> None:
    """tail must be allowed for /var/log paths (used by read_logs syslog)."""
    allowed, reason = validate_command("tail", ["-n", "50", "/var/log/syslog"])
    assert allowed is True, f"tail /var/log/syslog should be allowed: {reason}"


def test_tail_is_blocked_for_etc_shadow() -> None:
    """tail must be blocked for sensitive paths outside /var/log."""
    allowed, _ = validate_command("tail", ["-n", "50", "/etc/shadow"])
    assert allowed is False


def test_dmesg_time_format_flag_accepted() -> None:
    """dmesg --time-format=iso must be in the allowlist."""
    allowed, reason = validate_command("dmesg", ["--time-format=iso"])
    assert allowed is True, f"dmesg --time-format=iso should be allowed: {reason}"


def test_dmesg_level_flag_accepted() -> None:
    """dmesg --level err must be in the allowlist."""
    allowed, reason = validate_command("dmesg", ["--time-format=iso", "--level", "err"])
    assert allowed is True, f"dmesg --level err should be allowed: {reason}"


def test_unknown_command_rejected() -> None:
    """A command not in allowed or blocked list is rejected."""
    allowed, reason = validate_command("whoami", [])
    assert allowed is False
    assert "not present in the allowed commands set" in reason


def test_empty_command_rejected() -> None:
    """An empty string command is rejected."""
    allowed, _ = validate_command("", [])
    assert allowed is False


def test_path_traversal_blocked() -> None:
    """Path traversal attempts like /var/../etc/shadow must be blocked."""
    # The literal path doesn't start with an allowed prefix after traversal
    # This tests the raw prefix check — it catches obvious attempts
    allowed, _ = validate_command("cat", ["/etc/../etc/shadow"])
    assert allowed is False


def test_redirect_in_args_blocked() -> None:
    """Output redirection operators must be blocked."""
    allowed, reason = validate_command("ps", ["aux", ">", "/tmp/out"])
    assert allowed is False
    assert "illegal shell operator" in reason.lower()


# ── Tool edge cases: empty & error output ───────────────────────────


@pytest.mark.asyncio
async def test_check_processes_empty_stdout(mock_ssh: MagicMock) -> None:
    """check_processes handles empty stdout gracefully."""
    mock_ssh.execute.return_value = CommandResult(
        command="ps",
        args=["aux", "--sort=-%cpu"],
        stdout="",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_processes(mock_ssh, sort_by="cpu", limit=10)
    assert output.tool_name == "check_processes"
    assert output.exit_code == 0
    # Should not crash — just return empty


@pytest.mark.asyncio
async def test_check_processes_blocked_by_allowlist(
    mock_ssh: MagicMock,
) -> None:
    """check_processes returns blocked result when allowlist rejects."""
    mock_ssh.execute.return_value = CommandResult(
        command="ps",
        args=["aux", "--sort=-%cpu"],
        stdout="",
        stderr="Command blocked by allowlist policy",
        exit_code=-1,
        allowed=False,
    )

    output = await check_processes(mock_ssh, sort_by="cpu")
    assert output.allowed is False
    assert output.exit_code == -1


@pytest.mark.asyncio
async def test_check_service_status_both_fail(
    mock_ssh: MagicMock,
) -> None:
    """check_service_status handles both commands returning errors."""
    mock_ssh.execute.return_value = CommandResult(
        command="systemctl",
        args=[],
        stdout="",
        stderr="Unit not found",
        exit_code=4,
        allowed=True,
    )

    output = await check_service_status(
        mock_ssh, service_name="nonexistent"
    )
    assert output.exit_code == 4
    assert output.allowed is True


@pytest.mark.asyncio
async def test_check_disk_usage_no_path(mock_ssh: MagicMock) -> None:
    """check_disk_usage with no path should only call df, not du."""
    mock_ssh.execute.return_value = CommandResult(
        command="df",
        args=["-h"],
        stdout="/dev/sda1 20G 10G 10G 50% /",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_disk_usage(mock_ssh)

    # Only df should be called, not du
    mock_ssh.execute.assert_called_once_with("df", ["-h"])
    assert "FILESYSTEM OVERVIEW" in output.stdout
    assert "DIRECTORY USAGE" not in output.stdout


@pytest.mark.asyncio
async def test_check_memory_empty_meminfo(mock_ssh: MagicMock) -> None:
    """check_memory handles empty /proc/meminfo."""

    def mock_execute(
        command: str, args: list[str]
    ) -> CommandResult:
        if command == "free":
            return CommandResult(
                command="free",
                args=args,
                stdout="Mem: 8000 4000 4000",
                stderr="",
                exit_code=0,
                allowed=True,
            )
        return CommandResult(
            command="cat",
            args=args,
            stdout="",
            stderr="No such file",
            exit_code=1,
            allowed=True,
        )

    mock_ssh.execute.side_effect = mock_execute

    output = await check_memory(mock_ssh)
    assert "MEMORY OVERVIEW" in output.stdout
    # Should not crash even with empty meminfo
    assert output.exit_code == 1  # max of 0, 1


@pytest.mark.asyncio
async def test_check_dns_dig_failure(mock_ssh: MagicMock) -> None:
    """check_dns handles dig failure gracefully."""

    def mock_execute(
        command: str, args: list[str]
    ) -> CommandResult:
        if command == "dig":
            return CommandResult(
                command="dig",
                args=args,
                stdout="",
                stderr="connection timed out",
                exit_code=9,
                allowed=True,
            )
        return CommandResult(
            command="cat",
            args=args,
            stdout="nameserver 8.8.8.8",
            stderr="",
            exit_code=0,
            allowed=True,
        )

    mock_ssh.execute.side_effect = mock_execute

    output = await check_dns(mock_ssh, domain="broken.local")
    assert output.exit_code == 9
    assert "dig stderr: connection timed out" in output.stderr


@pytest.mark.asyncio
async def test_read_logs_dmesg_truncation(mock_ssh: MagicMock) -> None:
    """read_logs dmesg truncates to requested line count."""
    # Generate 100 lines of dmesg output
    dmesg_lines = [f"[T{i}] kernel message {i}" for i in range(100)]
    mock_ssh.execute.return_value = CommandResult(
        command="dmesg",
        args=["--time-format=iso"],
        stdout="\n".join(dmesg_lines),
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await read_logs(mock_ssh, source="dmesg", lines=10)

    result_lines = output.stdout.strip().split("\n")
    assert len(result_lines) == 10
    # Should be the LAST 10 lines (most recent)
    assert "kernel message 99" in result_lines[-1]
    assert "kernel message 90" in result_lines[0]


@pytest.mark.asyncio
async def test_read_logs_journalctl_with_level_filter(
    mock_ssh: MagicMock,
) -> None:
    """read_logs passes -p flag when level != 'all'."""
    mock_ssh.execute.return_value = CommandResult(
        command="journalctl",
        args=["-u", "nginx", "-n", "30", "--no-pager", "-p", "err"],
        stdout="Error log line",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await read_logs(
        mock_ssh,
        source="service",
        service_name="nginx",
        lines=30,
        level="err",
    )

    mock_ssh.execute.assert_called_once_with(
        "journalctl",
        ["-u", "nginx", "-n", "30", "--no-pager", "-p", "err"],
    )
    assert output.stdout == "Error log line"


# ── Registry edge cases ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_tool_bad_args(mock_ssh: MagicMock) -> None:
    """execute_tool handles unexpected args from LLM without crashing."""
    # Pass an arg that check_processes doesn't accept
    output = await execute_tool(
        "check_processes",
        {"sort_by": "cpu", "nonexistent_param": "bad"},
        mock_ssh,
    )
    # Should return error ToolOutput, not raise
    assert output.exit_code == -1
    assert "Exception" in output.stderr


@pytest.mark.asyncio
async def test_check_connectivity_default_ping(
    mock_ssh: MagicMock,
) -> None:
    """check_connectivity defaults to ping with -W 3 timeout."""
    mock_ssh.execute.return_value = CommandResult(
        command="ping",
        args=["-c", "4", "-W", "3", "10.0.0.1"],
        stdout="Request timeout",
        stderr="",
        exit_code=1,
        allowed=True,
    )

    output = await check_connectivity(mock_ssh, target="10.0.0.1")
    assert output.exit_code == 1
    assert output.tool_name == "check_connectivity"
