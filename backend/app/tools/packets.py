"""Scapy-based packet capture and TCP analysis tool.

Unlike other diagnostic tools that execute commands over SSH, this tool
runs Scapy LOCALLY on the backend host. It sniffs the network interface
directly and produces a structured text summary for the AI agent.
"""

from collections import defaultdict
from typing import Any

from scapy.all import IP, TCP, sniff  # type: ignore[attr-defined]

from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput, register_tool

# Maximum capture duration to prevent runaway sniffs
MAX_CAPTURE_SECONDS = 30

CAPTURE_PACKETS_SCHEMA = {
    "name": "capture_packets",
    "description": (
        "Capture and analyze network packets for a short duration. "
        "Detects TCP retransmissions, duplicate ACKs, and connection "
        "resets. Use when packet loss or network-level issues are "
        "suspected."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "interface": {
                "type": "string",
                "description": (
                    "Network interface to capture on "
                    "(default: primary interface)"
                ),
            },
            "duration_seconds": {
                "type": "integer",
                "description": (
                    "How long to capture packets "
                    "(default: 10, max: 30)"
                ),
                "default": 10,
            },
            "filter": {
                "type": "string",
                "description": (
                    "BPF filter expression (e.g., 'tcp port 80')"
                ),
            },
        },
    },
}


def _analyze_packets(packets: list[Any]) -> dict[str, Any]:
    """Analyze a list of Scapy packets for TCP anomalies.

    Returns a dict with:
        total_packets, tcp_packets, retransmissions, duplicate_acks,
        rst_count, syn_count, fin_count, retransmission_ratio
    """
    total = len(packets)
    tcp_count = 0
    retransmissions = 0
    duplicate_acks = 0
    rst_count = 0
    syn_count = 0
    fin_count = 0

    # Track seen (src, dst, sport, dport, seq) for retransmission detection
    seen_seq: set[tuple[str, str, int, int, int]] = set()

    # Track ACK numbers per flow for duplicate ACK detection
    ack_tracker: dict[tuple[str, str, int, int], list[int]] = defaultdict(list)

    for pkt in packets:
        if not pkt.haslayer(TCP):
            continue

        tcp_count += 1
        ip_layer = pkt[IP]
        tcp_layer = pkt[TCP]

        src: str = ip_layer.src
        dst: str = ip_layer.dst
        sport = tcp_layer.sport
        dport = tcp_layer.dport
        seq = tcp_layer.seq
        ack = tcp_layer.ack
        flags = tcp_layer.flags

        # Check TCP flags
        if flags.R:
            rst_count += 1
        if flags.S:
            syn_count += 1
        if flags.F:
            fin_count += 1

        # Retransmission detection: same flow + same seq seen before
        # Skip SYN and SYN-ACK retransmissions (normal TCP handshake)
        if not flags.S:
            flow_seq = (src, dst, sport, dport, seq)
            if flow_seq in seen_seq:
                retransmissions += 1
            else:
                seen_seq.add(flow_seq)

        # Duplicate ACK detection: same ACK number repeated in same flow
        if flags.A and not flags.S:
            flow_key = (src, dst, sport, dport)
            ack_list = ack_tracker[flow_key]
            if ack_list and ack_list[-1] == ack:
                duplicate_acks += 1
            ack_list.append(ack)

    retransmission_ratio = (
        round((retransmissions / tcp_count) * 100, 2) if tcp_count > 0 else 0.0
    )

    return {
        "total_packets": total,
        "tcp_packets": tcp_count,
        "retransmissions": retransmissions,
        "duplicate_acks": duplicate_acks,
        "rst_count": rst_count,
        "syn_count": syn_count,
        "fin_count": fin_count,
        "retransmission_ratio": retransmission_ratio,
    }


def _format_analysis(analysis: dict[str, Any], duration: int) -> str:
    """Format the analysis dict into human-readable text for the LLM."""
    lines = [
        f"--- PACKET CAPTURE SUMMARY ({duration}s) ---",
        f"Total packets captured: {analysis['total_packets']}",
        f"TCP packets: {analysis['tcp_packets']}",
        "",
        "--- TCP ANOMALY ANALYSIS ---",
        f"Retransmissions: {analysis['retransmissions']}",
        f"Duplicate ACKs: {analysis['duplicate_acks']}",
        f"TCP RST (Reset) packets: {analysis['rst_count']}",
        f"TCP SYN packets: {analysis['syn_count']}",
        f"TCP FIN packets: {analysis['fin_count']}",
        f"Retransmission ratio: {analysis['retransmission_ratio']}%",
        "",
        "--- INTERPRETATION ---",
    ]

    ratio = float(str(analysis["retransmission_ratio"]))
    if ratio == 0.0 and int(str(analysis["tcp_packets"])) > 0:
        lines.append("No retransmissions detected. TCP health appears normal.")
    elif ratio < 1.0:
        lines.append("Low retransmission rate. Minor packet loss may be present.")
    elif ratio < 5.0:
        lines.append("MODERATE retransmission rate. Noticeable packet loss.")
    elif ratio < 15.0:
        lines.append("HIGH retransmission rate. Significant packet loss detected.")
    else:
        lines.append(
            "CRITICAL retransmission rate. Severe packet loss — "
            "likely network interface or path issue."
        )

    rst = int(str(analysis["rst_count"]))
    if rst > 10:
        lines.append(
            f"WARNING: {rst} TCP RST packets detected — "
            f"connections are being forcefully terminated."
        )

    if int(str(analysis["total_packets"])) == 0:
        lines.clear()
        lines.append(
            f"--- PACKET CAPTURE SUMMARY ({duration}s) ---"
        )
        lines.append("No packets captured during the capture window.")
        lines.append(
            "This could indicate: no traffic on the interface, "
            "wrong interface selected, or insufficient permissions "
            "(CAP_NET_RAW required)."
        )

    return "\n".join(lines)


@register_tool(name="capture_packets", schema=CAPTURE_PACKETS_SCHEMA)
async def capture_packets(
    ssh_runner: SSHRunner,
    interface: str | None = None,
    duration_seconds: int = 10,
    filter: str | None = None,
) -> ToolOutput:
    """Capture packets locally via Scapy and analyze for TCP anomalies.

    Note: ssh_runner is accepted for interface consistency with the
    tool registry but is NOT used — Scapy runs locally on the backend.
    """
    # Clamp duration to prevent runaway captures
    duration = min(max(duration_seconds, 1), MAX_CAPTURE_SECONDS)

    # Build sniff kwargs
    sniff_kwargs: dict[str, object] = {"timeout": duration}

    if interface:
        sniff_kwargs["iface"] = interface

    if filter:
        sniff_kwargs["filter"] = filter

    try:
        captured = sniff(**sniff_kwargs)
        packets_list: list[Any] = list(captured)

        analysis = _analyze_packets(packets_list)
        summary = _format_analysis(analysis, duration)

        return ToolOutput(
            tool_name="capture_packets",
            stdout=summary,
            stderr="",
            exit_code=0,
            duration_ms=duration * 1000,
            allowed=True,
        )
    except PermissionError:
        return ToolOutput(
            tool_name="capture_packets",
            stdout="",
            stderr=(
                "Permission denied: packet capture requires "
                "CAP_NET_RAW capability or root privileges."
            ),
            exit_code=-1,
            allowed=True,
        )
    except OSError as err:
        return ToolOutput(
            tool_name="capture_packets",
            stdout="",
            stderr=f"Network capture error: {err}",
            exit_code=-1,
            allowed=True,
        )
