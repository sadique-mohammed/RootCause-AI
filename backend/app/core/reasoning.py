"""Core reasoning engine loop."""

import json
import logging
from typing import Any

from pydantic import ValidationError

from backend.app.api.schemas import DiagnosisReport
from backend.app.config import settings
from backend.app.core.llm import chat_completion
from backend.app.core.ssh_runner import SSHRunner
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


async def run_diagnosis(
    incident_description: str,
    ssh_runner: SSHRunner,
) -> DiagnosisReport:
    """
    Execute a full diagnostic investigation.

    Runs a loop:
    1. Send context to LLM.
    2. If it returns tool calls, execute them, truncate output, append, and continue.
    3. If it returns text, try to parse as DiagnosisReport JSON.
    4. Guard against >15 iterations.
    """
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

    for iteration in range(1, settings.max_tool_iterations + 1):
        logger.info("Diagnosis loop iteration %d/%d", iteration, settings.max_tool_iterations)

        response = await chat_completion(messages=messages, tools=tools)

        # 1. Handle Hard LLM Errors
        if response.error:
            logger.error("Reasoning loop aborted due to LLM error: %s", response.content)
            return DiagnosisReport(
                root_cause="LLM routing or API failure",
                root_cause_category="unknown",
                confidence=0.0,
                evidence=[],
                suggested_fix="Check LLM API status and API keys.",
                inconclusive=True,
                summary=f"Failed to diagnose due to backend AI error: {response.content}",
            )

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

        # 2. Handle Tool Calls
        if response.tool_calls:
            for tc in response.tool_calls:
                logger.info("Executing tool %s with args %s", tc.name, tc.arguments)
                tool_output = await execute_tool(
                    tc.name, tc.arguments, ssh_runner=ssh_runner
                )

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

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": truncated_text,
                    }
                )

            # Continue loop to let LLM analyze the tool results
            continue

        # 3. Handle Text Response (Final Diagnosis attempt)
        if response.content:
            raw_json = _extract_json_from_text(response.content)
            try:
                report = DiagnosisReport.model_validate_json(raw_json)

                # Check confidence/evidence rules
                if not report.evidence or report.confidence < 0.65:
                    report.inconclusive = True

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
    return DiagnosisReport(
        root_cause="Investigation timed out / max iterations reached.",
        root_cause_category="unknown",
        confidence=0.0,
        evidence=[],
        suggested_fix="Manual intervention required.",
        inconclusive=True,
        summary="The AI agent ran out of iterations before determining a conclusive root cause.",
    )
