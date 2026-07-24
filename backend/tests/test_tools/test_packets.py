"""Unit tests for Scapy packet capture and TCP analysis tool."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.packets import (
    _analyze_packets,
    _format_analysis,
    capture_packets,
)


@pytest.fixture
def mock_ssh() -> MagicMock:
    """Provide a mock SSHRunner (unused by capture_packets but required)."""
    return MagicMock(spec=SSHRunner)


def _make_tcp_packet(
    src: str = "10.0.0.1",
    dst: str = "10.0.0.2",
    sport: int = 12345,
    dport: int = 80,
    seq: int = 1000,
    ack: int = 2000,
    flags: str = "A",
) -> MagicMock:
    """Create a mock Scapy TCP/IP packet."""
    pkt = MagicMock()
    pkt.haslayer.return_value = True

    # IP layer
    ip_layer = MagicMock()
    ip_layer.src = src
    ip_layer.dst = dst

    # TCP layer
    tcp_layer = MagicMock()
    tcp_layer.sport = sport
    tcp_layer.dport = dport
    tcp_layer.seq = seq
    tcp_layer.ack = ack

    # Flag attributes
    tcp_layer.flags = MagicMock()
    tcp_layer.flags.R = "R" in flags
    tcp_layer.flags.S = "S" in flags
    tcp_layer.flags.F = "F" in flags
    tcp_layer.flags.A = "A" in flags

    pkt.__getitem__ = lambda self, cls: (
        ip_layer if cls.__name__ == "IP" else tcp_layer
    )

    return pkt


# ── _analyze_packets unit tests ─────────────────────────────────────


def test_analyze_empty_capture() -> None:
    """Empty capture returns zeroes across the board."""
    result = _analyze_packets([])
    assert result["total_packets"] == 0
    assert result["tcp_packets"] == 0
    assert result["retransmissions"] == 0
    assert result["retransmission_ratio"] == 0.0


def test_analyze_normal_traffic() -> None:
    """Normal traffic with unique seq numbers has 0 retransmissions."""
    packets = [
        _make_tcp_packet(seq=1000, ack=2000),
        _make_tcp_packet(seq=1001, ack=2001),
        _make_tcp_packet(seq=1002, ack=2002),
        _make_tcp_packet(seq=1003, ack=2003),
    ]
    result = _analyze_packets(packets)

    assert result["total_packets"] == 4
    assert result["tcp_packets"] == 4
    assert result["retransmissions"] == 0
    assert result["retransmission_ratio"] == 0.0


def test_analyze_retransmissions() -> None:
    """Duplicate sequence numbers are counted as retransmissions."""
    packets = [
        _make_tcp_packet(seq=1000, ack=2000),
        _make_tcp_packet(seq=1001, ack=2001),
        # Retransmission: seq 1000 seen again from same flow
        _make_tcp_packet(seq=1000, ack=2000),
        _make_tcp_packet(seq=1002, ack=2002),
    ]
    result = _analyze_packets(packets)

    assert result["retransmissions"] == 1
    assert result["retransmission_ratio"] == 25.0  # 1/4 = 25%


def test_analyze_duplicate_acks() -> None:
    """Same ACK number repeated in sequence is a duplicate ACK."""
    packets = [
        _make_tcp_packet(seq=1000, ack=2000),
        # Duplicate ACK: same ack from same flow
        _make_tcp_packet(seq=1001, ack=2000),
        # Another dup ACK
        _make_tcp_packet(seq=1002, ack=2000),
        _make_tcp_packet(seq=1003, ack=2001),
    ]
    result = _analyze_packets(packets)

    assert result["duplicate_acks"] == 2


def test_analyze_rst_packets() -> None:
    """RST-flagged packets are counted."""
    packets = [
        _make_tcp_packet(seq=1000, flags="A"),
        _make_tcp_packet(seq=1001, flags="R"),
        _make_tcp_packet(seq=1002, flags="R"),
    ]
    result = _analyze_packets(packets)

    assert result["rst_count"] == 2


def test_analyze_syn_not_counted_as_retransmission() -> None:
    """SYN packets with same seq should NOT be counted as retransmissions."""
    packets = [
        _make_tcp_packet(seq=0, flags="S"),
        # SYN retransmit — should be excluded from retransmission count
        _make_tcp_packet(seq=0, flags="S"),
    ]
    result = _analyze_packets(packets)

    assert result["syn_count"] == 2
    assert result["retransmissions"] == 0


# ── _format_analysis unit tests ─────────────────────────────────────


def test_format_normal_traffic() -> None:
    """Normal traffic produces 'TCP health appears normal' message."""
    analysis: dict[str, Any] = {
        "total_packets": 100,
        "tcp_packets": 80,
        "retransmissions": 0,
        "duplicate_acks": 0,
        "rst_count": 0,
        "syn_count": 5,
        "fin_count": 5,
        "retransmission_ratio": 0.0,
    }
    text = _format_analysis(analysis, duration=10)
    assert "TCP health appears normal" in text


def test_format_high_retransmission() -> None:
    """High retransmission ratio produces warning."""
    analysis: dict[str, Any] = {
        "total_packets": 100,
        "tcp_packets": 100,
        "retransmissions": 10,
        "duplicate_acks": 5,
        "rst_count": 0,
        "syn_count": 0,
        "fin_count": 0,
        "retransmission_ratio": 10.0,
    }
    text = _format_analysis(analysis, duration=10)
    assert "HIGH retransmission rate" in text


def test_format_empty_capture() -> None:
    """Empty capture produces 'no packets captured' message."""
    analysis: dict[str, Any] = {
        "total_packets": 0,
        "tcp_packets": 0,
        "retransmissions": 0,
        "duplicate_acks": 0,
        "rst_count": 0,
        "syn_count": 0,
        "fin_count": 0,
        "retransmission_ratio": 0.0,
    }
    text = _format_analysis(analysis, duration=10)
    assert "No packets captured" in text


def test_format_rst_flood_warning() -> None:
    """Many RST packets produce a specific warning."""
    analysis: dict[str, Any] = {
        "total_packets": 100,
        "tcp_packets": 100,
        "retransmissions": 0,
        "duplicate_acks": 0,
        "rst_count": 15,
        "syn_count": 0,
        "fin_count": 0,
        "retransmission_ratio": 0.0,
    }
    text = _format_analysis(analysis, duration=10)
    assert "15 TCP RST packets detected" in text


# ── capture_packets integration tests ───────────────────────────────


@pytest.mark.asyncio
@patch("backend.app.tools.packets.sniff")
async def test_capture_packets_normal(
    mock_sniff: MagicMock,
    mock_ssh: MagicMock,
) -> None:
    """capture_packets returns structured ToolOutput."""
    mock_sniff.return_value = [
        _make_tcp_packet(seq=1000),
        _make_tcp_packet(seq=1001),
    ]

    output = await capture_packets(mock_ssh, duration_seconds=5)

    assert output.tool_name == "capture_packets"
    assert output.exit_code == 0
    assert output.allowed is True
    assert "Total packets captured: 2" in output.stdout
    mock_sniff.assert_called_once()


@pytest.mark.asyncio
@patch("backend.app.tools.packets.sniff")
async def test_capture_packets_with_filter(
    mock_sniff: MagicMock,
    mock_ssh: MagicMock,
) -> None:
    """capture_packets passes BPF filter to sniff."""
    mock_sniff.return_value = []

    await capture_packets(
        mock_ssh,
        filter="tcp port 80",
        duration_seconds=5,
    )

    call_kwargs = mock_sniff.call_args[1]
    assert call_kwargs["filter"] == "tcp port 80"
    assert call_kwargs["timeout"] == 5


@pytest.mark.asyncio
@patch("backend.app.tools.packets.sniff")
async def test_capture_packets_clamps_duration(
    mock_sniff: MagicMock,
    mock_ssh: MagicMock,
) -> None:
    """Duration is clamped to MAX_CAPTURE_SECONDS (30)."""
    mock_sniff.return_value = []

    await capture_packets(mock_ssh, duration_seconds=999)

    call_kwargs = mock_sniff.call_args[1]
    assert call_kwargs["timeout"] == 30


@pytest.mark.asyncio
@patch("backend.app.tools.packets.sniff")
async def test_capture_packets_permission_error(
    mock_sniff: MagicMock,
    mock_ssh: MagicMock,
) -> None:
    """PermissionError returns structured error ToolOutput."""
    mock_sniff.side_effect = PermissionError("Operation not permitted")

    output = await capture_packets(mock_ssh)

    assert output.exit_code == -1
    assert "Permission denied" in output.stderr
    assert "CAP_NET_RAW" in output.stderr


@pytest.mark.asyncio
@patch("backend.app.tools.packets.sniff")
async def test_capture_packets_os_error(
    mock_sniff: MagicMock,
    mock_ssh: MagicMock,
) -> None:
    """OSError returns structured error ToolOutput."""
    mock_sniff.side_effect = OSError("No such device")

    output = await capture_packets(mock_ssh)

    assert output.exit_code == -1
    assert "No such device" in output.stderr
