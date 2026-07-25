"""Unit tests for the reasoning engine loop."""

from unittest.mock import MagicMock, patch

import pytest

from backend.app.api.schemas import DiagnosisReport, EvidenceItem
from backend.app.core.llm import LLMResponse, TokenUsage, ToolCall
from backend.app.core.reasoning import _truncate_output, run_diagnosis
from backend.app.core.ssh_runner import SSHRunner
from backend.app.tools.registry import ToolOutput


def _make_dummy_report() -> DiagnosisReport:
    return DiagnosisReport(
        root_cause="Test",
        root_cause_category="process",
        confidence=0.9,
        evidence=[
            EvidenceItem(
                step=1,
                tool_name="test",
                tool_args={},
                raw_output="test",
                key_finding="test",
                relevance="test",
                supports_conclusion=True,
            )
        ],
        suggested_fix="Fix",
        summary="Summary",
    )


def test_truncate_output() -> None:
    """Test the truncation guard enforces the max_output_length."""
    with patch("backend.app.core.reasoning.settings") as mock_settings:
        mock_settings.max_output_length = 10

        assert _truncate_output("short") == "short"
        assert _truncate_output("exactlyten") == "exactlyten"
        assert _truncate_output("elevenchars") == "elevenchar\n...[TRUNCATED]"


@pytest.mark.asyncio
@patch("backend.app.core.reasoning.execute_tool")
@patch("backend.app.core.reasoning.chat_completion")
@patch("backend.app.core.reasoning.settings")
async def test_run_diagnosis_immediate_success(
    mock_settings: MagicMock,
    mock_chat: MagicMock,
    mock_execute: MagicMock,
) -> None:
    """Test the loop returning a valid report on the first iteration."""
    mock_settings.max_tool_iterations = 15
    mock_settings.system_prompt = "SYS"

    dummy_report = _make_dummy_report()

    mock_chat.return_value = LLMResponse(
        content=dummy_report.model_dump_json(),
        usage=TokenUsage(),
        model="mock",
    )

    ssh_runner = MagicMock(spec=SSHRunner)

    report = await run_diagnosis("Test incident", ssh_runner)

    assert report.root_cause == "Test"
    assert report.inconclusive is False
    mock_execute.assert_not_called()
    assert mock_chat.call_count == 1


@pytest.mark.asyncio
@patch("backend.app.core.reasoning.execute_tool")
@patch("backend.app.core.reasoning.chat_completion")
@patch("backend.app.core.reasoning.settings")
async def test_run_diagnosis_with_tool_calls(
    mock_settings: MagicMock,
    mock_chat: MagicMock,
    mock_execute: MagicMock,
) -> None:
    """Test the loop executing a tool then returning a report."""
    mock_settings.max_tool_iterations = 15
    mock_settings.system_prompt = "SYS"
    mock_settings.max_output_length = 2000

    dummy_report = _make_dummy_report()

    # 1st turn: Tool call
    # 2nd turn: Final report
    mock_chat.side_effect = [
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="call_1", name="check_disk", arguments={"path": "/"})],
            usage=TokenUsage(),
            model="mock",
        ),
        LLMResponse(
            content=dummy_report.model_dump_json(),
            usage=TokenUsage(),
            model="mock",
        ),
    ]

    mock_execute.return_value = ToolOutput(
        tool_name="dummy", stdout="disk is full", stderr="", exit_code=0, allowed=True
    )

    ssh_runner = MagicMock(spec=SSHRunner)

    report = await run_diagnosis("Test incident", ssh_runner)

    assert report.root_cause == "Test"
    assert mock_execute.call_count == 1
    assert mock_chat.call_count == 2

    # Check that the tool result was passed in the chat calls
    all_messages = mock_chat.call_args_list[1].kwargs["messages"]
    tool_messages = [m for m in all_messages if m["role"] == "tool"]
    assert len(tool_messages) > 0
    assert "disk is full" in tool_messages[-1]["content"]


@pytest.mark.asyncio
@patch("backend.app.core.reasoning.execute_tool")
@patch("backend.app.core.reasoning.chat_completion")
@patch("backend.app.core.reasoning.settings")
async def test_run_diagnosis_max_iterations(
    mock_settings: MagicMock,
    mock_chat: MagicMock,
    mock_execute: MagicMock,
) -> None:
    """Test the loop aborts and returns inconclusive at max iterations."""
    mock_settings.max_tool_iterations = 3
    mock_settings.system_prompt = "SYS"
    mock_settings.max_output_length = 2000

    # LLM keeps returning tool calls forever
    mock_chat.return_value = LLMResponse(
        content=None,
        tool_calls=[ToolCall(id="call_x", name="dummy", arguments={})],
        usage=TokenUsage(),
        model="mock",
    )

    mock_execute.return_value = ToolOutput(
        tool_name="dummy", stdout="data", stderr="", exit_code=0, allowed=True
    )

    ssh_runner = MagicMock(spec=SSHRunner)

    report = await run_diagnosis("Test incident", ssh_runner)

    assert report.inconclusive is True
    assert report.root_cause_category == "unknown"
    assert "max iterations reached" in report.root_cause
    assert mock_execute.call_count == 3
    assert mock_chat.call_count == 3


@pytest.mark.asyncio
@patch("backend.app.core.reasoning.execute_tool")
@patch("backend.app.core.reasoning.chat_completion")
@patch("backend.app.core.reasoning.settings")
async def test_run_diagnosis_invalid_json_recovery(
    mock_settings: MagicMock,
    mock_chat: MagicMock,
    mock_execute: MagicMock,
) -> None:
    """Test the loop recovers if the LLM outputs invalid JSON once."""
    mock_settings.max_tool_iterations = 3
    mock_settings.system_prompt = "SYS"

    dummy_report = _make_dummy_report()

    # 1st turn: Invalid JSON
    # 2nd turn: Valid JSON
    mock_chat.side_effect = [
        LLMResponse(content="{bad json", usage=TokenUsage(), model="mock"),
        LLMResponse(content=dummy_report.model_dump_json(), usage=TokenUsage(), model="mock"),
    ]

    ssh_runner = MagicMock(spec=SSHRunner)
    report = await run_diagnosis("Test incident", ssh_runner)

    assert report.root_cause == "Test"
    assert mock_chat.call_count == 2

    # Check that the validation error was fed back
    all_messages = mock_chat.call_args_list[1].kwargs["messages"]
    user_messages = [m for m in all_messages if m.get("role") == "user"]
    assert len(user_messages) == 2  # The initial one + the error feedback
    assert "was not valid JSON matching the DiagnosisReport schema" in user_messages[-1].get("content", "")


@pytest.mark.asyncio
@patch("backend.app.core.reasoning.execute_tool")
@patch("backend.app.core.reasoning.chat_completion")
@patch("backend.app.core.reasoning.settings")
async def test_run_diagnosis_llm_error(
    mock_settings: MagicMock,
    mock_chat: MagicMock,
    mock_execute: MagicMock,
) -> None:
    """Test the loop aborts if the LLM encounters a hard error."""
    mock_settings.max_tool_iterations = 3
    mock_settings.system_prompt = "SYS"

    mock_chat.return_value = LLMResponse(
        error=True,
        content="Rate limit exceeded",
        usage=TokenUsage(),
        model="mock",
    )

    ssh_runner = MagicMock(spec=SSHRunner)
    report = await run_diagnosis("Test incident", ssh_runner)

    assert report.inconclusive is True
    assert "LLM routing or API failure" in report.root_cause
    assert mock_chat.call_count == 1
    assert mock_execute.call_count == 0
