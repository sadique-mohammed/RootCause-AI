"""Paramiko SSH Runner with structured command execution and connection management."""

import time
from datetime import UTC, datetime
from typing import Any

import paramiko
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.core.allowlist import validate_command


class CommandResult(BaseModel):
    """Structured output returned by the SSH runner for any command execution."""

    command: str = Field(description="Base command name")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    exit_code: int = Field(default=0, description="Process exit code (-1 for connection/execution error)")
    duration_ms: int = Field(default=0, description="Execution duration in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Execution timestamp")
    allowed: bool = Field(default=True, description="Whether the command passed allowlist validation")


class SSHRunner:
    """Paramiko SSH client wrapper with allowlist enforcement and structured output."""

    def __init__(
        self,
        host: str | None = None,
        username: str | None = None,
        key_path: str | None = None,
        password: str | None = None,
        timeout: int = 10,
    ) -> None:
        self.host = host or settings.target_host
        self.username = username or settings.target_user
        self.key_path = key_path or settings.target_ssh_key
        self.password = password or settings.target_password
        self.timeout = timeout
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        """Establish SSH connection using Paramiko."""
        if self._client is not None:
            return

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: dict[str, Any] = {
            "hostname": self.host,
            "username": self.username,
            "timeout": self.timeout,
        }

        if self.key_path:
            import os

            expanded_key = os.path.expanduser(self.key_path)
            if os.path.exists(expanded_key):
                connect_kwargs["key_filename"] = expanded_key

        if self.password:
            connect_kwargs["password"] = self.password

        try:
            client.connect(**connect_kwargs)
            self._client = client
        except Exception as err:
            raise RuntimeError(f"SSH connection failed to {self.username}@{self.host}: {err}") from err

    def ping_connection(self) -> bool:
        """Synchronously ping/verify the SSH connection (pre-flight check)."""
        try:
            self.connect()
            result = self.execute("free", ["-m"], timeout=5)
            return result.allowed and result.exit_code == 0
        except Exception:
            return False

    def execute(self, command: str, args: list[str] | None = None, timeout: int = 15) -> CommandResult:
        """Validate command against allowlist, execute via Paramiko if allowed, and return CommandResult."""
        args_list = args or []
        start_time = time.perf_counter()

        # Step 1: Security Allowlist Gate
        is_allowed, reason = validate_command(command, args_list)
        if not is_allowed:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return CommandResult(
                command=command,
                args=args_list,
                stdout="",
                stderr=f"Command blocked by allowlist policy: {reason}",
                exit_code=-1,
                duration_ms=duration_ms,
                allowed=False,
            )

        # Step 2: Ensure SSH connection is active
        try:
            self.connect()
        except Exception as err:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return CommandResult(
                command=command,
                args=args_list,
                stdout="",
                stderr=str(err),
                exit_code=-1,
                duration_ms=duration_ms,
                allowed=True,
            )

        assert self._client is not None

        # Step 3: Format full command with PAGER=cat to avoid interactive hangs
        full_command = f"PAGER=cat {command} {' '.join(args_list)}".strip()

        try:
            stdin, stdout_stream, stderr_stream = self._client.exec_command(full_command, timeout=timeout)
            stdin.close()

            stdout_text = stdout_stream.read().decode("utf-8", errors="replace")
            stderr_text = stderr_stream.read().decode("utf-8", errors="replace")
            exit_code = stdout_stream.channel.recv_exit_status()

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            return CommandResult(
                command=command,
                args=args_list,
                stdout=stdout_text,
                stderr=stderr_text,
                exit_code=exit_code,
                duration_ms=duration_ms,
                allowed=True,
            )
        except Exception as err:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return CommandResult(
                command=command,
                args=args_list,
                stdout="",
                stderr=f"SSH execution error: {err}",
                exit_code=-1,
                duration_ms=duration_ms,
                allowed=True,
            )

    def disconnect(self) -> None:
        """Close Paramiko SSH channel."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            finally:
                self._client = None
