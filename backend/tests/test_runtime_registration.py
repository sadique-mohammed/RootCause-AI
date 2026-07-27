"""Tests for application startup wiring."""

from backend.app.tools.registry import TOOL_REGISTRY


def test_production_tools_are_registered() -> None:
    """Importing the application package must register every production tool."""
    expected = {
        "check_processes",
        "check_service_status",
        "check_disk_usage",
        "check_memory",
        "check_network_interfaces",
        "check_routes",
        "check_listening_ports",
        "check_dns",
        "check_certificates",
        "read_logs",
        "capture_packets",
        "check_connectivity",
    }
    assert expected <= TOOL_REGISTRY.keys()
