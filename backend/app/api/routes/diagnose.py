"""Diagnosis API endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.app.api.schemas import DiagnoseRequest, DiagnosisRunRead, EvidenceItemRead
from backend.app.config import settings
from backend.app.core.reasoning import run_diagnosis
from backend.app.core.ssh_runner import SSHRunner
from backend.app.db.database import get_db_session
from backend.app.db.models import DiagnosisRun, EvidenceItemDB

router = APIRouter(tags=["Diagnosis"])


@router.post("/diagnose", status_code=status.HTTP_202_ACCEPTED)
async def start_diagnosis(
    request: DiagnoseRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, Any]:
    """Start a new diagnosis run asynchronously."""

    # 1. Pre-flight SSH check
    host = request.target_host or settings.target_host
    username = request.ssh_username or settings.target_user
    key_path = request.ssh_key_path or settings.target_ssh_key
    password = request.ssh_password or settings.target_password

    runner = SSHRunner(
        host=host,
        username=username,
        key_path=key_path,
        password=password,
    )

    if not runner.ping_connection():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Pre-flight SSH ping failed for {username}@{host}. Check credentials or host reachability.",
        )

    # 2. Create DB entry
    run_db = DiagnosisRun(
        target_host=host,
        incident_description=request.incident_description,
        status="pending",
    )
    db_session.add(run_db)
    await db_session.commit()
    await db_session.refresh(run_db)

    # 3. Launch background task
    background_tasks.add_task(
        run_diagnosis,
        incident_description=request.incident_description,
        ssh_runner=runner,
        run_id=run_db.id,
        db_session=db_session,
    )

    return {"run_id": str(run_db.id), "status": "pending"}


@router.get("/diagnose/{run_id}", response_model=DiagnosisRunRead)
async def get_diagnosis(
    run_id: uuid.UUID,
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> DiagnosisRunRead:
    """Fetch the status and results of a diagnosis run."""
    run_db = await db_session.get(DiagnosisRun, run_id)
    if not run_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis run not found",
        )

    # Fetch evidence items
    stmt = select(EvidenceItemDB).where(EvidenceItemDB.run_id == run_id).order_by(EvidenceItemDB.step_number)  # type: ignore[arg-type]
    result = await db_session.execute(stmt)
    evidence_dbs = result.scalars().all()

    evidence = [
        EvidenceItemRead(
            id=ev.id,
            run_id=ev.run_id,
            created_at=ev.created_at,
            step=ev.step_number,
            tool_name=ev.tool_name,
            tool_args=ev.tool_args,
            raw_output=ev.raw_output,
            key_finding=ev.key_finding,
            relevance=ev.relevance,
            supports_conclusion=ev.supports_conclusion,
        )
        for ev in evidence_dbs
    ]

    return DiagnosisRunRead(
        id=run_db.id,
        target_host=run_db.target_host,
        incident_description=run_db.incident_description,
        status=run_db.status,
        commands_executed=run_db.commands_executed,
        duration_seconds=run_db.duration_seconds,
        created_at=run_db.created_at,
        completed_at=run_db.completed_at,
        root_cause=run_db.root_cause,
        root_cause_category=run_db.root_cause_category,
        confidence=run_db.confidence,
        suggested_fix=run_db.suggested_fix,
        evidence=evidence,
    )
