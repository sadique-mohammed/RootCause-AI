"""Hardcoded command allowlist validator for SSH command safety."""

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
            "/etc/nginx/nginx.conf",
        ],
    ),
    "ping": AllowedCommandSpec(allowed_flags=["-c", "-i", "-W", "-s", "-q"]),
    "traceroute": AllowedCommandSpec(allowed_flags=["-m", "-n", "-q", "-w"]),
    "ip": AllowedCommandSpec(allowed_flags=["route", "link", "addr", "show", "-s", "-4", "-6"]),
    "ss": AllowedCommandSpec(allowed_flags=["-tlnp", "-ulnp", "-tulpn", "-a", "-s", "-t", "-u", "-l", "-p", "-n"]),
    "dig": AllowedCommandSpec(allowed_flags=["+time=", "+tries=", "+short", "A", "AAAA", "MX", "TXT", "NS", "ANY"]),
    "nslookup": AllowedCommandSpec(allowed_flags=[]),
    "openssl": AllowedCommandSpec(
        allowed_flags=["s_client", "x509", "-connect", "-servername", "-enddate", "-noout", "-dates", "-issuer"]
    ),
    "dmesg": AllowedCommandSpec(allowed_flags=["--level=", "-T", "-L", "-e", "-k"]),
    "uptime": AllowedCommandSpec(allowed_flags=[]),
    "uname": AllowedCommandSpec(allowed_flags=["-a", "-r", "-m", "-s", "-v"]),
}


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

    # Check 4: If command has path restrictions (e.g., cat, du, ls), verify path arguments
    if spec.restricted_paths:
        paths = [a for a in args_list if not a.startswith("-")]
        for path in paths:
            clean_path = path.strip()
            # Must start with one of the allowed restricted path prefixes
            if not any(clean_path.startswith(prefix) for prefix in spec.restricted_paths):
                msg = (
                    f"Path '{clean_path}' for command '{base_cmd}' "
                    f"is outside restricted path prefixes: {spec.restricted_paths}"
                )
                return False, msg

    return True, "OK"
