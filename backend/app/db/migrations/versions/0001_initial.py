"""Initial RootCause AI database schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the diagnosis, evidence, and command audit tables."""
    op.create_table(
        "diagnosis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_host", sa.String(), nullable=False),
        sa.Column("incident_description", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("root_cause_category", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("inconclusive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("alternative_hypotheses", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("commands_executed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diagnosis_runs_target_host", "diagnosis_runs", ["target_host"])
    op.create_index("ix_diagnosis_runs_status", "diagnosis_runs", ["status"])

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("tool_args", sa.JSON(), nullable=False),
        sa.Column("raw_output", sa.Text(), nullable=False),
        sa.Column("key_finding", sa.Text(), nullable=False),
        sa.Column("relevance", sa.Text(), nullable=False),
        sa.Column("supports_conclusion", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["diagnosis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_items_run_id", "evidence_items", ["run_id"])

    op.create_table(
        "command_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("args", sa.JSON(), nullable=False),
        sa.Column("stdout", sa.Text(), nullable=False),
        sa.Column("stderr", sa.Text(), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["diagnosis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_command_log_run_id", "command_log", ["run_id"])


def downgrade() -> None:
    """Drop the diagnosis tables."""
    op.drop_index("ix_command_log_run_id", table_name="command_log")
    op.drop_table("command_log")
    op.drop_index("ix_evidence_items_run_id", table_name="evidence_items")
    op.drop_table("evidence_items")
    op.drop_index("ix_diagnosis_runs_status", table_name="diagnosis_runs")
    op.drop_index("ix_diagnosis_runs_target_host", table_name="diagnosis_runs")
    op.drop_table("diagnosis_runs")
