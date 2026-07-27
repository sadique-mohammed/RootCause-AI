"""Tests for database models."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.app.db.models import CommandLog, DiagnosisRun, EvidenceItemDB


@pytest.mark.asyncio
async def test_create_diagnosis_run(db_session: AsyncSession) -> None:
    """Test creating and retrieving a DiagnosisRun."""
    run = DiagnosisRun(
        target_host="10.0.0.1",
        incident_description="Test incident",
        status="running",
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    assert run.id is not None
    assert run.target_host == "10.0.0.1"
    assert run.status == "running"

    # Retrieve
    fetched = await db_session.get(DiagnosisRun, run.id)
    assert fetched is not None
    assert fetched.incident_description == "Test incident"


@pytest.mark.asyncio
async def test_evidence_item_relationship(db_session: AsyncSession) -> None:
    """Test adding EvidenceItems to a DiagnosisRun."""
    run = DiagnosisRun(
        target_host="10.0.0.1",
        incident_description="Test incident",
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    ev = EvidenceItemDB(
        run_id=run.id,
        step_number=1,
        tool_name="test_tool",
        tool_args={"arg1": "val1"},
        raw_output="raw",
        key_finding="found it",
        relevance="high",
        supports_conclusion=True,
    )
    db_session.add(ev)
    await db_session.commit()

    stmt = select(EvidenceItemDB).where(EvidenceItemDB.run_id == run.id)
    result = await db_session.execute(stmt)
    evidence_items = result.scalars().all()

    assert len(evidence_items) == 1
    assert evidence_items[0].tool_name == "test_tool"
    assert evidence_items[0].tool_args == {"arg1": "val1"}


@pytest.mark.asyncio
async def test_command_log_relationship(db_session: AsyncSession) -> None:
    """Test adding CommandLogs to a DiagnosisRun."""
    run = DiagnosisRun(
        target_host="10.0.0.1",
        incident_description="Test incident",
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    cmd = CommandLog(
        run_id=run.id,
        command="ps",
        args=["aux"],
        stdout="pid 1",
        stderr="",
        exit_code=0,
        duration_ms=42,
        allowed=True,
    )
    db_session.add(cmd)
    await db_session.commit()

    stmt = select(CommandLog).where(CommandLog.run_id == run.id)
    result = await db_session.execute(stmt)
    logs = result.scalars().all()

    assert len(logs) == 1
    assert logs[0].command == "ps"
    assert logs[0].args == ["aux"]
    assert logs[0].allowed is True
