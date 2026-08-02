"""Pydantic schemas for the REST API and AI Reasoning output."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """A single piece of evidence from a diagnostic command."""

    step: int = Field(description="Order this evidence was collected (1-indexed)")
    tool_name: str = Field(description="Which diagnostic tool was called")
    tool_args: dict[str, Any] = Field(description="Arguments passed to the tool")
    raw_output: str = Field(description="Command output snippet")
    key_finding: str = Field(
        description="What the agent observed. Must cite specific values/lines."
    )
    relevance: str = Field(description="Why this finding matters to the diagnosis")
    supports_conclusion: bool = Field(
        description="Does this evidence support the final root cause conclusion?"
    )


class DiagnosisReport(BaseModel):
    """Final diagnosis produced by the AI agent."""

    root_cause: str = Field(
        description="Plain-English description of what's wrong. 1-3 sentences."
    )
    root_cause_category: Literal[
        "process",
        "service",
        "disk",
        "memory",
        "network",
        "dns",
        "tls",
        "tcp",
        "routing",
        "unknown",
    ] = Field(description="Classification of the root cause type.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Agent's confidence in this diagnosis. 0.0 = no idea, 1.0 = certain.",
    )
    evidence: list[EvidenceItem] = Field(
        description="Ordered list of evidence supporting the diagnosis."
    )
    suggested_fix: str = Field(
        description="Recommended remediation step. Description only — agent does not execute fixes."
    )
    alternative_hypotheses: list[str] = Field(
        default_factory=list,
        description="Other possible causes considered and why they were ruled out.",
    )
    inconclusive: bool = Field(
        default=False,
        description="True if the agent could not determine a root cause.",
    )
    summary: str | None = Field(
        default=None,
        description="One-paragraph executive summary suitable for a status update."
    )


class DiagnoseRequest(BaseModel):
    """Input payload to trigger a new diagnostic run."""

    target_host: str | None = Field(
        default=None,
        description="IP/Host of target VM. Overrides env settings if provided."
    )
    incident_description: str = Field(description="Description of the incident or symptoms")

    # Optional runtime SSH credentials override
    ssh_username: str | None = None
    ssh_key_path: str | None = None
    ssh_password: str | None = None


class EvidenceItemRead(EvidenceItem):
    """API view of an EvidenceItem, extending it with DB IDs."""
    id: uuid.UUID
    run_id: uuid.UUID
    created_at: datetime


class DiagnosisRunRead(BaseModel):
    """API view of a full DiagnosisRun."""

    id: uuid.UUID
    target_host: str
    incident_description: str

    status: str
    commands_executed: int
    duration_seconds: float

    created_at: datetime
    completed_at: datetime | None

    # Fields from DiagnosisReport
    root_cause: str | None
    root_cause_category: str | None
    confidence: float | None
    suggested_fix: str | None
    summary: str | None
    inconclusive: bool
    alternative_hypotheses: list[str]

    # Nested evidence
    evidence: list[EvidenceItemRead] = Field(default_factory=list)


class CommandLogRead(BaseModel):
    """API view of one executed or blocked command."""

    id: uuid.UUID
    run_id: uuid.UUID
    command: str
    args: list[str]
    exit_code: int
    duration_ms: int
    allowed: bool
    executed_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str | None = None
    llm_model: str | None = None
