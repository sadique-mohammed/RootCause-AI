"""Core reasoning engine loop."""

import asyncio
import contextlib
import json
import logging
import time
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.tools  # noqa: F401  # Registers production tools on import.
from backend.app.api.schemas import DiagnosisReport
from backend.app.config import settings
from backend.app.core.llm import chat_completion
from backend.app.core.ssh_runner import SSHRunner
from backend.app.db.models import CommandLog, DiagnosisRun, EvidenceItemDB
from backend.app.tools.registry import execute_tool, get_all_tool_schemas

logger = logging.getLogger(__name__)


def _truncate_output(text: str) -> str:
    """Strictly enforce the output truncation limit to protect context window."""
    limit = settings.max_output_length
    if len(text) > limit:
        return text[:limit] + "\n...[TRUNCATED]"
    return text


def _extract_json_from_text(text: str) -> str:
    """Attempt to extract a JSON object from markdown code blocks or plain text."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def _evidence_is_grounded(report: DiagnosisReport, observations: list[tuple[str, str]]) -> bool:
    """Require every cited raw-output snippet to come from an executed tool."""
    if not report.evidence:
        return False
    for evidence in report.evidence:
        if not evidence.raw_output.strip():
            return False
        if not any(
            evidence.tool_name == tool_name and evidence.raw_output.strip() in output
            for tool_name, output in observations
        ):
            return False
    return True


async def run_diagnosis(
    incident_description: str,
    ssh_runner: SSHRunner,
    run_id: uuid.UUID | None = None,
    db_session: AsyncSession | None = None,
) -> DiagnosisReport:
    """
    Execute a full diagnostic investigation.

    Runs a loop:
    1. Send context to LLM.
    2. If it returns tool calls, execute them, truncate output, append, and continue.
    3. If it returns text, try to parse as DiagnosisReport JSON.
    4. Guard against >15 iterations.
    5. Save everything to DB if provided.
    """
    if run_id is not None and db_session is None:
        from backend.app.db.database import async_session_maker

        async with async_session_maker() as owned_session:
            return await run_diagnosis(
                incident_description=incident_description,
                ssh_runner=ssh_runner,
                run_id=run_id,
                db_session=owned_session,
            )

    # 0. Set status to running in DB
    run_db = None
    if run_id and db_session:
        run_db = await db_session.get(DiagnosisRun, run_id)
        if run_db:
            run_db.status = "running"
            await db_session.commit()
    system_prompt = (
        settings.system_prompt
        + "\n\nWhen you are ready to produce your final diagnosis, or if you run out of ideas, "
        "you MUST return a single, valid JSON object matching the DiagnosisReport schema as your text response. "
        "Do NOT return anything else. Do NOT ask clarifying questions."
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Investigate this incident:\n\n{incident_description}",
        },
    ]

    tools = get_all_tool_schemas()
    observations: list[tuple[str, str]] = []
    configured_timeout = getattr(settings, "diagnosis_timeout_seconds", 120)
    timeout_seconds = configured_timeout if isinstance(configured_timeout, (int, float)) else 120
    deadline = time.monotonic() + timeout_seconds
    tool_calls_executed = 0

    try:
        for iteration in range(1, settings.max_tool_iterations + 1):
            logger.info("Diagnosis loop iteration %d/%d", iteration, settings.max_tool_iterations)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            try:
                response = await asyncio.wait_for(
                    chat_completion(messages=messages, tools=tools), timeout=remaining
                )
            except TimeoutError:
                break

            # 1. Handle Hard LLM Errors
            if response.error:
                logger.error("Reasoning loop aborted due to LLM error: %s", response.content)
                final_report = DiagnosisReport(
                    root_cause="LLM routing or API failure",
                    root_cause_category="unknown",
                    confidence=0.0,
                    evidence=[],
                    suggested_fix="Check LLM API status and API keys.",
                    inconclusive=True,
                    summary=f"Failed to diagnose due to backend AI error: {response.content}",
                )
                await _persist_to_db(run_db, final_report, ssh_runner, db_session)
                return final_report

            # 2. Check Tool Call Budget (BEFORE appending to avoid malformed history)
            if response.tool_calls and tool_calls_executed + len(response.tool_calls) > settings.max_tool_iterations:
                break

            # Append assistant's response to history
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if response.content:
                assistant_msg["content"] = response.content
            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in response.tool_calls
                ]
            messages.append(assistant_msg)

            # 3. Execute Tool Calls
            if response.tool_calls:
                timed_out = False
                for tc in response.tool_calls:
                    logger.info("Executing tool %s with args %s", tc.name, tc.arguments)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        break
                    try:
                        tool_output = await asyncio.wait_for(
                            execute_tool(tc.name, tc.arguments, ssh_runner=ssh_runner),
                            timeout=remaining,
                        )
                    except TimeoutError:
                        timed_out = True
                        break
                    tool_calls_executed += 1

                    # Format output
                    if tool_output.allowed:
                        raw_text = (
                            f"EXIT_CODE: {tool_output.exit_code}\n"
                            f"STDOUT:\n{tool_output.stdout}\n"
                            f"STDERR:\n{tool_output.stderr}"
                        )
                    else:
                        raw_text = f"BLOCKED BY SECURITY ALLOWLIST: {tool_output.stderr}"

                    truncated_text = _truncate_output(raw_text)
                    observations.append((tc.name, raw_text))

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": truncated_text,
                        }
                    )

                if timed_out:
                    break
                # Continue loop to let LLM analyze the tool results
                continue

            # 3. Handle Text Response (Final Diagnosis attempt)
            if response.content:
                raw_json = _extract_json_from_text(response.content)
                try:
                    report = DiagnosisReport.model_validate_json(raw_json)

                    # Check confidence/evidence rules
                    if not _evidence_is_grounded(report, observations) or report.confidence < 0.65:
                        report.inconclusive = True

                    await _persist_to_db(run_db, report, ssh_runner, db_session)
                    return report

                except ValidationError as e:
                    logger.warning("Failed to parse DiagnosisReport JSON: %s", e)
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Your response was not valid JSON matching the "
                                f"DiagnosisReport schema. Please fix it. Error: {e}"
                            ),
                        }
                    )
                    continue

        # 4. Hit iteration limit
        logger.warning("Max iterations (%d) reached.", settings.max_tool_iterations)
        final_report = DiagnosisReport(
            root_cause="Investigation timed out / max iterations reached.",
            root_cause_category="unknown",
            confidence=0.0,
            evidence=[],
            suggested_fix="Manual intervention required.",
            inconclusive=True,
            summary="The AI agent ran out of iterations before determining a conclusive root cause.",
        )
        await _persist_to_db(run_db, final_report, ssh_runner, db_session)
        return final_report
    except Exception as exc:
        logger.exception("Unhandled error in diagnosis loop")
        if run_db and db_session:
            run_db.status = "failed"
            run_db.summary = f"Internal error: {exc}"
            with contextlib.suppress(SQLAlchemyError):
                await db_session.commit()
        raise
    finally:
        ssh_runner.disconnect()


async def _persist_to_db(
    run_db: DiagnosisRun | None,
    report: DiagnosisReport,
    ssh_runner: SSHRunner,
    db_session: AsyncSession | None,
) -> None:
    """Helper to persist the diagnosis run, evidence, and commands to the DB."""
    if not run_db or not db_session:
        return

    from datetime import UTC, datetime

    # 1. Update the DiagnosisRun
    run_db.status = "inconclusive" if report.inconclusive else "completed"
    run_db.root_cause = report.root_cause
    run_db.root_cause_category = report.root_cause_category
    run_db.confidence = report.confidence
    run_db.suggested_fix = report.suggested_fix
    run_db.summary = report.summary
    run_db.inconclusive = report.inconclusive
    run_db.alternative_hypotheses = report.alternative_hypotheses
    run_db.commands_executed = len(ssh_runner.command_history)
    run_db.completed_at = datetime.now(UTC).replace(tzinfo=None)

    # Calculate duration safely (both datetimes are naive UTC)
    if run_db.created_at:
        created_at = run_db.created_at
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        delta = run_db.completed_at - created_at
        run_db.duration_seconds = delta.total_seconds()

    db_session.add(run_db)

    # 2. Add EvidenceItems
    for ev in report.evidence:
        ev_db = EvidenceItemDB(
            run_id=run_db.id,
            step_number=ev.step,
            tool_name=ev.tool_name,
            tool_args=ev.tool_args,
            raw_output=ev.raw_output,
            key_finding=ev.key_finding,
            relevance=ev.relevance,
            supports_conclusion=ev.supports_conclusion,
        )
        db_session.add(ev_db)

    # 3. Add CommandLogs
    for cmd in ssh_runner.command_history:
        cmd_db = CommandLog(
            run_id=run_db.id,
            command=cmd.command,
            args=cmd.args,
            stdout=cmd.stdout,
            stderr=cmd.stderr,
            exit_code=cmd.exit_code,
            duration_ms=cmd.duration_ms,
            allowed=cmd.allowed,
            executed_at=cmd.timestamp,
        )
        db_session.add(cmd_db)

    try:
        await db_session.commit()
    except SQLAlchemyError as e:
        logger.error("Failed to commit diagnosis run to DB: %s", e)
        await db_session.rollback()
