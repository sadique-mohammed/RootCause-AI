"""SQLModel database definitions for RootCause AI."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

# SQLite compat for JSON/JSONB
JSON_VARIANT = JSON().with_variant(JSONB, "postgresql")


class DiagnosisRun(SQLModel, table=True):
    """Tracks a single diagnostic investigation run."""

    __tablename__ = "diagnosis_runs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    target_host: str = Field(index=True)
    incident_description: str

    root_cause: str | None = None
    root_cause_category: str | None = None
    confidence: float | None = None
    suggested_fix: str | None = None

    status: str = Field(default="pending", index=True)
    commands_executed: int = Field(default=0)
    duration_seconds: float = Field(default=0.0)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("TIMEZONE('utc', CURRENT_TIMESTAMP)")},
    )
    completed_at: datetime | None = None


class EvidenceItemDB(SQLModel, table=True):
    """A single piece of evidence cited by the AI during a run."""

    __tablename__ = "evidence_items"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    run_id: uuid.UUID = Field(foreign_key="diagnosis_runs.id", index=True)

    step_number: int
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON_VARIANT))
    raw_output: str
    key_finding: str
    relevance: str
    supports_conclusion: bool

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("TIMEZONE('utc', CURRENT_TIMESTAMP)")},
    )


class CommandLog(SQLModel, table=True):
    """Log of every command executed or blocked by the SSH runner."""

    __tablename__ = "command_log"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    run_id: uuid.UUID = Field(foreign_key="diagnosis_runs.id", index=True)

    command: str
    args: list[str] = Field(default_factory=list, sa_column=Column(JSON_VARIANT))

    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    allowed: bool

    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("TIMEZONE('utc', CURRENT_TIMESTAMP)")},
    )
