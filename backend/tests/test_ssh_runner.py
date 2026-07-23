"""Unit tests for SSHRunner with Paramiko mocking."""

from unittest.mock import MagicMock, patch

from backend.app.core.ssh_runner import SSHRunner


def test_ssh_runner_allowlist_blocking() -> None:
    """Test that SSHRunner rejects blocked commands without opening SSH channel."""
    runner = SSHRunner(host="127.0.0.1", username="test")

    # Should be rejected at the runner layer without calling connect()
    with patch.object(runner, "connect") as mock_connect:
        res = runner.execute("rm", ["-rf", "/var/log"])

        assert res.allowed is False
        assert res.exit_code == -1
        assert "blocked by allowlist" in res.stderr
        mock_connect.assert_not_called()


def test_ssh_runner_allowed_command_mocked() -> None:
    """Test SSHRunner executing an allowed command with mocked Paramiko channel."""
    runner = SSHRunner(host="127.0.0.1", username="test")

    mock_client = MagicMock()
    mock_stdin = MagicMock()
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()

    mock_stdout.read.return_value = b"Mem: 16000 8000 8000\n"
    mock_stderr.read.return_value = b""
    mock_stdout.channel.recv_exit_status.return_value = 0

    mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
    runner._client = mock_client

    res = runner.execute("free", ["-m"])

    assert res.allowed is True
    assert res.exit_code == 0
    assert "Mem: 16000" in res.stdout
    assert res.stderr == ""
    mock_client.exec_command.assert_called_once_with("PAGER=cat free -m", timeout=15)
