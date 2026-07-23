"""Unit tests for network and forensics diagnostic tools (Phase 2.2)."""

from unittest.mock import MagicMock

import pytest

from backend.app.core.ssh_runner import CommandResult, SSHRunner
from backend.app.tools.certificate import check_certificates
from backend.app.tools.connectivity import check_connectivity
from backend.app.tools.dns import check_dns
from backend.app.tools.logs import read_logs
from backend.app.tools.network import check_network_interfaces, check_routes
from backend.app.tools.ports import check_listening_ports


@pytest.fixture
def mock_ssh() -> MagicMock:
    """Provide a mock SSHRunner."""
    return MagicMock(spec=SSHRunner)


# ── check_network_interfaces ────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_network_interfaces(mock_ssh: MagicMock) -> None:
    """Verify ip addr show is called and output is wrapped."""
    mock_ssh.execute.return_value = CommandResult(
        command="ip",
        args=["addr", "show"],
        stdout="1: lo: <LOOPBACK,UP> mtu 65536\n2: eth0: <UP>",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_network_interfaces(mock_ssh)

    mock_ssh.execute.assert_called_once_with("ip", ["addr", "show"])
    assert output.tool_name == "check_network_interfaces"
    assert "eth0" in output.stdout
    assert output.exit_code == 0


# ── check_routes ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_routes(mock_ssh: MagicMock) -> None:
    """Verify ip route show is called and output is wrapped."""
    mock_ssh.execute.return_value = CommandResult(
        command="ip",
        args=["route", "show"],
        stdout="default via 10.0.0.1 dev eth0\n10.0.0.0/24 dev eth0",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_routes(mock_ssh)

    mock_ssh.execute.assert_called_once_with("ip", ["route", "show"])
    assert "default via 10.0.0.1" in output.stdout


# ── check_listening_ports ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_listening_ports_tcp(mock_ssh: MagicMock) -> None:
    """Verify ss -tlnp is called for TCP filter."""
    mock_ssh.execute.return_value = CommandResult(
        command="ss",
        args=["-tlnp"],
        stdout="LISTEN 0 128 *:80 *:* users:((\"nginx\",pid=1234))",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_listening_ports(mock_ssh, protocol="tcp")

    mock_ssh.execute.assert_called_once_with("ss", ["-tlnp"])
    assert "nginx" in output.stdout


@pytest.mark.asyncio
async def test_check_listening_ports_all(mock_ssh: MagicMock) -> None:
    """Verify ss -tulnp is called for 'all' (default)."""
    mock_ssh.execute.return_value = CommandResult(
        command="ss",
        args=["-tulnp"],
        stdout="LISTEN 0 128 *:53 *:*",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_listening_ports(mock_ssh)

    mock_ssh.execute.assert_called_once_with("ss", ["-tulnp"])
    assert output.tool_name == "check_listening_ports"


# ── check_dns ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_dns(mock_ssh: MagicMock) -> None:
    """Verify dig and resolv.conf are both queried."""

    def mock_execute(
        command: str, args: list[str]
    ) -> CommandResult:
        if command == "dig":
            return CommandResult(
                command="dig",
                args=args,
                stdout="142.250.80.46",
                stderr="",
                exit_code=0,
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

    output = await check_dns(mock_ssh, domain="example.com")

    assert mock_ssh.execute.call_count == 2
    assert "DIG example.com" in output.stdout
    assert "142.250.80.46" in output.stdout
    assert "nameserver 8.8.8.8" in output.stdout


# ── check_certificates ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_certificates(mock_ssh: MagicMock) -> None:
    """Verify openssl s_client is called with correct args."""
    mock_ssh.execute.return_value = CommandResult(
        command="openssl",
        args=[
            "s_client", "-connect", "example.com:443",
            "-servername", "example.com",
        ],
        stdout="subject=CN = example.com\nissuer=CN = R3",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_certificates(
        mock_ssh, host="example.com", port=443
    )

    mock_ssh.execute.assert_called_once_with(
        "openssl",
        [
            "s_client",
            "-connect",
            "example.com:443",
            "-servername",
            "example.com",
        ],
    )
    assert "CN = example.com" in output.stdout


# ── read_logs ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_read_logs_service(mock_ssh: MagicMock) -> None:
    """Verify journalctl is called for source='service'."""
    mock_ssh.execute.return_value = CommandResult(
        command="journalctl",
        args=["-u", "nginx", "-n", "20", "--no-pager"],
        stdout="Jul 23 nginx[1234]: started",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await read_logs(
        mock_ssh, source="service", service_name="nginx", lines=20
    )

    mock_ssh.execute.assert_called_once_with(
        "journalctl",
        ["-u", "nginx", "-n", "20", "--no-pager"],
    )
    assert "nginx" in output.stdout


@pytest.mark.asyncio
async def test_read_logs_service_missing_name(
    mock_ssh: MagicMock,
) -> None:
    """Return error when source='service' but service_name is None."""
    output = await read_logs(mock_ssh, source="service")

    assert output.exit_code == 1
    assert "service_name is required" in output.stderr
    mock_ssh.execute.assert_not_called()


@pytest.mark.asyncio
async def test_read_logs_dmesg(mock_ssh: MagicMock) -> None:
    """Verify dmesg is called for source='dmesg'."""
    mock_ssh.execute.return_value = CommandResult(
        command="dmesg",
        args=["--time-format=iso"],
        stdout="[T1] OOM killer invoked\n[T2] killed process",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await read_logs(mock_ssh, source="dmesg", lines=50)

    assert "OOM killer" in output.stdout


@pytest.mark.asyncio
async def test_read_logs_syslog(mock_ssh: MagicMock) -> None:
    """Verify tail is called for source='syslog'."""
    mock_ssh.execute.return_value = CommandResult(
        command="tail",
        args=["-n", "50", "/var/log/syslog"],
        stdout="Jul 23 syslog: message",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await read_logs(mock_ssh, source="syslog")

    mock_ssh.execute.assert_called_once_with(
        "tail", ["-n", "50", "/var/log/syslog"]
    )
    assert "syslog" in output.stdout


# ── check_connectivity ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_connectivity_ping(mock_ssh: MagicMock) -> None:
    """Verify ping is called with correct args."""
    mock_ssh.execute.return_value = CommandResult(
        command="ping",
        args=["-c", "4", "-W", "3", "8.8.8.8"],
        stdout="4 packets transmitted, 4 received, 0% loss",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_connectivity(mock_ssh, target="8.8.8.8")

    mock_ssh.execute.assert_called_once_with(
        "ping", ["-c", "4", "-W", "3", "8.8.8.8"]
    )
    assert "0% loss" in output.stdout


@pytest.mark.asyncio
async def test_check_connectivity_traceroute(
    mock_ssh: MagicMock,
) -> None:
    """Verify traceroute is called when method='traceroute'."""
    mock_ssh.execute.return_value = CommandResult(
        command="traceroute",
        args=["-m", "15", "8.8.8.8"],
        stdout="1  gateway (10.0.0.1)  1.234 ms",
        stderr="",
        exit_code=0,
        allowed=True,
    )

    output = await check_connectivity(
        mock_ssh, target="8.8.8.8", method="traceroute"
    )

    mock_ssh.execute.assert_called_once_with(
        "traceroute", ["-m", "15", "8.8.8.8"]
    )
    assert "gateway" in output.stdout
