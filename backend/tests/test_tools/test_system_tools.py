"""Unit tests for system and resource diagnostic tools."""

from unittest.mock import MagicMock

import pytest

from backend.app.core.ssh_runner import CommandResult, SSHRunner
from backend.app.tools.disk import check_disk_usage
from backend.app.tools.memory import check_memory
from backend.app.tools.process import check_processes
from backend.app.tools.service import check_service_status


@pytest.fixture
def mock_ssh_runner() -> MagicMock:
    """Provide a mock SSHRunner."""
    return MagicMock(spec=SSHRunner)


@pytest.mark.asyncio
async def test_check_processes(mock_ssh_runner: MagicMock) -> None:
    """Test check_processes tool execution."""

    mock_ssh_runner.execute.return_value = CommandResult(
        command="ps",
        args=["aux", "--sort=-%cpu"],
        stdout="USER PID %CPU %MEM\nroot 1 0.0 0.1\nuser 2 0.0 0.2",
        stderr="",
        exit_code=0,
        duration_ms=15,
        allowed=True
    )

    # Test cpu sorting
    output = await check_processes(mock_ssh_runner, sort_by="cpu", limit=1)

    mock_ssh_runner.execute.assert_called_once_with("ps", ["aux", "--sort=-%cpu"])
    assert output.tool_name == "check_processes"
    assert output.exit_code == 0
    assert output.allowed is True
    # The output should be limited to header + limit (2 lines total)
    assert "root 1 0.0 0.1" in output.stdout
    assert "user 2" not in output.stdout


@pytest.mark.asyncio
async def test_check_service_status(mock_ssh_runner: MagicMock) -> None:
    """Test check_service_status tool execution."""

    def mock_execute(command: str, args: list[str]) -> CommandResult:
        if command == "systemctl":
            return CommandResult(
                command="systemctl", args=args, stdout="Active: active (running)", stderr="", exit_code=0, allowed=True
            )
        elif command == "journalctl":
            return CommandResult(
                command="journalctl", args=args, stdout="Log line 1\nLog line 2", stderr="", exit_code=0, allowed=True
            )
        return CommandResult(command=command, args=args)

    mock_ssh_runner.execute.side_effect = mock_execute

    output = await check_service_status(mock_ssh_runner, service_name="nginx", log_lines=10)

    assert mock_ssh_runner.execute.call_count == 2
    assert "SYSTEMCTL STATUS" in output.stdout
    assert "Active: active (running)" in output.stdout
    assert "RECENT JOURNAL LOGS" in output.stdout
    assert "Log line 1" in output.stdout
    assert output.exit_code == 0
    assert output.allowed is True


@pytest.mark.asyncio
async def test_check_disk_usage(mock_ssh_runner: MagicMock) -> None:
    """Test check_disk_usage tool execution."""

    def mock_execute(command: str, args: list[str]) -> CommandResult:
        if command == "df":
            return CommandResult(
                command="df", args=args, stdout="/dev/sda1 20G 19G 1G 95% /", stderr="", exit_code=0, allowed=True
            )
        elif command == "du":
            return CommandResult(
                command="du", args=args, stdout="5G /var/log", stderr="", exit_code=0, allowed=True
            )
        return CommandResult(command=command, args=args)

    mock_ssh_runner.execute.side_effect = mock_execute

    # Test with path
    output = await check_disk_usage(mock_ssh_runner, path="/var/log")

    assert mock_ssh_runner.execute.call_count == 2
    assert "FILESYSTEM OVERVIEW (df -h)" in output.stdout
    assert "95% /" in output.stdout
    assert "DIRECTORY USAGE (du -sh /var/log)" in output.stdout
    assert "5G /var/log" in output.stdout


@pytest.mark.asyncio
async def test_check_memory(mock_ssh_runner: MagicMock) -> None:
    """Test check_memory tool execution."""

    def mock_execute(command: str, args: list[str]) -> CommandResult:
        if command == "free":
            return CommandResult(
                command="free", args=args, stdout="Mem: 16000 8000 8000", stderr="", exit_code=0, allowed=True
            )
        elif command == "cat":
            return CommandResult(
                command="cat",
                args=args,
                stdout="MemTotal: 16000 kB\nMemFree: 8000 kB",
                stderr="",
                exit_code=0,
                allowed=True
            )
        return CommandResult(command=command, args=args)

    mock_ssh_runner.execute.side_effect = mock_execute

    output = await check_memory(mock_ssh_runner)

    assert mock_ssh_runner.execute.call_count == 2
    assert "MEMORY OVERVIEW (free -m)" in output.stdout
    assert "Mem: 16000 8000 8000" in output.stdout
    assert "DETAILED STATS" in output.stdout
    assert "MemTotal: 16000 kB" in output.stdout
