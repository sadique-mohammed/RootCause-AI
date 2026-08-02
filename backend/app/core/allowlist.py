"""Hardcoded command allowlist validator for SSH command safety."""

import posixpath
import re

from pydantic import BaseModel, Field

# Blocked base commands that are never permitted under any circumstances
BLOCKED_COMMANDS: set[str] = {
    "rm",
    "kill",
    "pkill",
    "killall",
    "reboot",
    "shutdown",
    "poweroff",
    "chmod",
    "chown",
    "chgrp",
    "mv",
    "cp",
    "mkdir",
    "rmdir",
    "curl",
    "wget",
    "nc",
    "netcat",
    "ncat",
    "bash",
    "sh",
    "zsh",
    "dash",
    "csh",
    "sudo",
    "su",
    "passwd",
    "dd",
    "mkfs",
    "fdisk",
    "mount",
    "umount",
    "iptables",
    "nft",
    "ufw",
    "apt",
    "yum",
    "dnf",
    "pip",
    "npm",
    "python",
    "python3",
    "perl",
    "ruby",
    "node",
    "crontab",
    "at",
}


class AllowedCommandSpec(BaseModel):
    """Specification for an allowed base command and its acceptable arguments/paths."""

    allowed_flags: list[str] = Field(default_factory=list, description="Allowed flag prefixes")
    restricted_paths: list[str] = Field(default_factory=list, description="Allowed directory or file path prefixes")


ALLOWED_COMMANDS: dict[str, AllowedCommandSpec] = {
    "ps": AllowedCommandSpec(allowed_flags=["aux", "-ef", "--sort=-%mem", "--sort=-%cpu", "-u", "-p"]),
    "top": AllowedCommandSpec(allowed_flags=["-bn1", "-b", "-n", "-p"]),
    "systemctl": AllowedCommandSpec(
        allowed_flags=["status", "list-units", "is-active", "is-failed", "--no-pager"]
    ),
    "journalctl": AllowedCommandSpec(
        allowed_flags=["-u", "--since", "--until", "--no-pager", "-n", "-k", "-b", "-p", "--priority"]
    ),
    "df": AllowedCommandSpec(allowed_flags=["-h", "-k", "-m", "-i", "-T"]),
    "du": AllowedCommandSpec(
        allowed_flags=["-sh", "-h", "-m", "-k", "-d", "--max-depth"],
        restricted_paths=["/var", "/tmp", "/etc", "/home", "/opt", "/usr", "/srv"],
    ),
    "ls": AllowedCommandSpec(
        allowed_flags=["-la", "-lah", "-l", "-la", "-1", "-t", "-r"],
        restricted_paths=["/var", "/tmp", "/etc", "/home", "/opt", "/usr", "/srv"],
    ),
    "free": AllowedCommandSpec(allowed_flags=["-m", "-h", "-g", "-k", "-t"]),
    "cat": AllowedCommandSpec(
        allowed_flags=[],
        restricted_paths=[
            "/proc/meminfo",
            "/proc/cpuinfo",
            "/proc/version",
            "/proc/stat",
            "/etc/resolv.conf",
            "/etc/hosts",
            "/etc/nsswitch.conf",
            "/etc/nginx",
            "/var/log/nginx",
            "/var/log/syslog",
        ],
    ),
    "ping": AllowedCommandSpec(allowed_flags=["-c", "-i", "-W", "-s", "-q"]),
    "traceroute": AllowedCommandSpec(allowed_flags=["-m", "-n", "-q", "-w"]),
    "ip": AllowedCommandSpec(allowed_flags=["route", "link", "addr", "show", "-s", "-4", "-6"]),
    "ss": AllowedCommandSpec(
        allowed_flags=["-tlnp", "-ulnp", "-tulpn", "-tulnp", "-a", "-s", "-t", "-u", "-l", "-p", "-n"]
    ),
    "dig": AllowedCommandSpec(allowed_flags=["+time=", "+tries=", "+short", "A", "AAAA", "MX", "TXT", "NS", "ANY"]),
    "nslookup": AllowedCommandSpec(allowed_flags=[]),
    "openssl": AllowedCommandSpec(
        allowed_flags=[
            "s_client", "x509", "-connect", "-servername",
            "-enddate", "-noout", "-dates", "-issuer",
            "-in", "-text", "-fingerprint", "-subject",
        ],
        restricted_paths=["/etc/ssl", "/etc/nginx"],
    ),
    "dmesg": AllowedCommandSpec(allowed_flags=["--level=", "--level", "--time-format=iso", "-T", "-L", "-e", "-k"]),
    "uptime": AllowedCommandSpec(allowed_flags=[]),
    "uname": AllowedCommandSpec(allowed_flags=["-a", "-r", "-m", "-s", "-v"]),
    "tail": AllowedCommandSpec(
        allowed_flags=["-n", "-f"],
        restricted_paths=["/var/log"],
    ),
    "head": AllowedCommandSpec(
        allowed_flags=["-n"],
        restricted_paths=["/var/log"],
    ),
}

_SAFE_VALUE = re.compile(r"^[A-Za-z0-9_./:@%+=,-]+$")
_SAFE_FIRST_POSITIONAL_VALUES = {
    "systemctl": {"status", "list-units", "is-active", "is-failed"},
    "ip": {"route", "link", "addr", "show"},
}
_BLOCKED_POSITIONAL_OPERATIONS = {
    "add",
    "change",
    "del",
    "delete",
    "down",
    "enable",
    "flush",
    "replace",
    "restart",
    "set",
    "start",
    "stop",
    "up",
}
_ALLOWED_IP_SHAPES = {
    ("addr", "show"),
    ("link", "show"),
    ("route", "show"),
    ("show",),
}


def _path_matches_prefix(path: str, prefix: str) -> bool:
    """Match a path only when it is the prefix itself or a child of it."""
    return path == prefix or path.startswith(f"{prefix}/")


def _validate_arguments(command: str, args: list[str], spec: AllowedCommandSpec) -> tuple[bool, str]:
    """Validate flags, positional values, and restricted paths."""
    path_restricted = bool(spec.restricted_paths)

    for index, arg in enumerate(args):
        if not arg or not _SAFE_VALUE.fullmatch(arg):
            return False, f"Argument '{arg}' contains unsupported characters"

        if arg.startswith("/"):
            if not path_restricted:
                return False, f"Absolute path '{arg}' is not permitted for '{command}'"
            normalized = posixpath.normpath(arg)
            if normalized != arg:
                return False, f"Path traversal is not permitted: '{arg}'"
            if not any(_path_matches_prefix(arg, prefix) for prefix in spec.restricted_paths):
                return False, f"Path '{arg}' is outside the restricted paths for '{command}'"
            continue

        is_flag = arg.startswith("-") or arg.startswith("+")
        if is_flag:
            exact_match = arg in spec.allowed_flags
            prefix_match = any(flag.endswith("=") and arg.startswith(flag) for flag in spec.allowed_flags)
            if not (exact_match or prefix_match):
                return False, f"Flag '{arg}' is not permitted for '{command}'"
        if command in {"systemctl", "ip"} and not is_flag and arg in _BLOCKED_POSITIONAL_OPERATIONS:
            return False, f"Operation '{arg}' is not permitted for '{command}'"

        if (
            command in _SAFE_FIRST_POSITIONAL_VALUES
            and index == 0
            and arg not in _SAFE_FIRST_POSITIONAL_VALUES[command]
        ):
            return False, f"Operation '{arg}' is not permitted for '{command}'"

    if command == "ip":
        positional = tuple(arg for arg in args if not arg.startswith("-") and not arg.startswith("+"))
        if positional not in _ALLOWED_IP_SHAPES:
            return False, f"Argument shape '{' '.join(positional)}' is not permitted for 'ip'"

    if path_restricted and command in {"cat", "du", "ls", "tail", "head"}:
        positional_paths = [arg for arg in args if not arg.startswith("-") and not arg.startswith("+")]
        if command == "cat" and any(not arg.startswith("/") for arg in positional_paths):
            return False, "cat requires absolute, explicitly permitted paths"
        if command in {"tail", "head"} and not any(arg.startswith("/") for arg in args):
            return False, f"{command} requires an absolute, explicitly permitted path"

    return True, "OK"


def validate_command(command: str, args: list[str] | None = None) -> tuple[bool, str]:
    """
    Validate a base command and its arguments against the security allowlist.

    Returns:
        (True, "OK") if the command is allowed.
        (False, reason_string) if the command is blocked.
    """
    base_cmd = command.strip().lower()
    args_list = args or []

    # Check 1: Explicit blocked list
    if base_cmd in BLOCKED_COMMANDS:
        return False, f"Command '{base_cmd}' is in the explicit blocked commands list"

    # Check 2: Check for malicious shell injection characters in command or args
    forbidden_tokens = [";", "&&", "||", "|", "`", "$(", ">", ">>", "<", "\n", "\r"]
    full_str = f"{base_cmd} {' '.join(args_list)}"
    for token in forbidden_tokens:
        if token in full_str:
            return False, f"Command contains illegal shell operator '{token}'"

    # Check 3: Allowed base command check
    if base_cmd not in ALLOWED_COMMANDS:
        return False, f"Command '{base_cmd}' is not present in the allowed commands set"

    spec = ALLOWED_COMMANDS[base_cmd]
    return _validate_arguments(base_cmd, args_list, spec)
