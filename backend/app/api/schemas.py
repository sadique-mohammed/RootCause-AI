"""Pydantic schemas for the REST API and AI Reasoning output."""

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """A single piece of evidence from a diagnostic command."""

    step: int = Field(description="Order this evidence was collected (1-indexed)")
    tool_name: str = Field(description="Which diagnostic tool was called")
    tool_args: dict[str, str] = Field(description="Arguments passed to the tool")
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
    summary: str = Field(
        description="One-paragraph executive summary suitable for a status update."
    )
