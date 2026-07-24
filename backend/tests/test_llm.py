"""Unit tests for LiteLLM abstraction layer."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litellm.exceptions import (
    APIError as LiteLLMAPIError,
)
from litellm.exceptions import (
    Timeout as LiteLLMTimeout,
)

from backend.app.core.llm import (
    LLMResponse,
    TokenUsage,
    ToolCall,
    _extract_usage,
    _parse_tool_calls,
    _resolve_model_name,
    chat_completion,
)

# ── Model name resolution ──────────────────────────────────────────


@patch("backend.app.core.llm.settings")
def test_resolve_model_name_ollama(mock_settings: MagicMock) -> None:
    """Ollama models are prefixed with 'ollama/'."""
    mock_settings.litellm_provider = "ollama"
    mock_settings.ollama_model = "llama3.1:8b"

    result = _resolve_model_name()
    assert result == "ollama/llama3.1:8b"


@patch("backend.app.core.llm.settings")
def test_resolve_model_name_openai(mock_settings: MagicMock) -> None:
    """OpenAI models are passed as-is without prefix."""
    mock_settings.litellm_provider = "openai"
    mock_settings.openai_model = "gpt-4o"

    result = _resolve_model_name()
    assert result == "gpt-4o"


# ── Tool call parsing ──────────────────────────────────────────────


def _make_raw_tool_call(
    call_id: str = "call_123",
    name: str = "check_disk_usage",
    arguments: str | dict[str, Any] = '{"path": "/var"}',
) -> MagicMock:
    """Create a mock raw tool call object matching LiteLLM's response format."""
    tc = MagicMock()
    tc.id = call_id
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


def test_parse_tool_calls_valid() -> None:
    """Valid tool call with JSON arguments is parsed correctly."""
    raw = [_make_raw_tool_call()]
    result = _parse_tool_calls(raw)

    assert len(result) == 1
    assert result[0].id == "call_123"
    assert result[0].name == "check_disk_usage"
    assert result[0].arguments == {"path": "/var"}


def test_parse_tool_calls_multiple() -> None:
    """Multiple tool calls are all parsed."""
    raw = [
        _make_raw_tool_call(call_id="call_1", name="check_memory"),
        _make_raw_tool_call(call_id="call_2", name="check_processes"),
    ]
    result = _parse_tool_calls(raw)

    assert len(result) == 2
    assert result[0].name == "check_memory"
    assert result[1].name == "check_processes"


def test_parse_tool_calls_invalid_json_arguments() -> None:
    """Invalid JSON in arguments falls back to empty dict."""
    raw = [_make_raw_tool_call(arguments="not valid json {{")]
    result = _parse_tool_calls(raw)

    assert len(result) == 1
    assert result[0].arguments == {}


def test_parse_tool_calls_dict_arguments() -> None:
    """Arguments already as dict (some providers) are passed through."""
    raw = [_make_raw_tool_call(arguments={"path": "/var"})]
    result = _parse_tool_calls(raw)

    assert result[0].arguments == {"path": "/var"}


def test_parse_tool_calls_malformed_object() -> None:
    """Malformed tool call objects are silently skipped."""
    bad_tc = MagicMock(spec=[])  # No .function attribute
    raw = [bad_tc]
    result = _parse_tool_calls(raw)

    assert len(result) == 0


# ── Token usage extraction ─────────────────────────────────────────


def test_extract_usage_valid() -> None:
    """Usage object with all fields is extracted correctly."""
    raw = MagicMock()
    raw.prompt_tokens = 100
    raw.completion_tokens = 50
    raw.total_tokens = 150

    result = _extract_usage(raw)
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50
    assert result.total_tokens == 150


def test_extract_usage_none() -> None:
    """None usage returns zero-filled TokenUsage."""
    result = _extract_usage(None)
    assert result.prompt_tokens == 0
    assert result.total_tokens == 0


def test_extract_usage_missing_fields() -> None:
    """Missing usage fields default to 0."""
    raw = MagicMock(spec=[])  # No attributes
    result = _extract_usage(raw)
    assert result.prompt_tokens == 0


# ── Helpers for chat_completion tests ────────────────────────────────


def _make_llm_response(
    content: str | None = "Hello!",
    tool_calls: list[Any] | None = None,
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> MagicMock:
    """Create a mock LiteLLM response."""
    response = MagicMock()

    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message
    response.choices = [choice]

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = prompt_tokens + completion_tokens
    response.usage = usage

    return response


# ── chat_completion: text response ──────────────────────────────────


@pytest.mark.asyncio
@patch("backend.app.core.llm.litellm")
@patch("backend.app.core.llm.settings")
async def test_chat_completion_text_response(
    mock_settings: MagicMock,
    mock_litellm: MagicMock,
) -> None:
    """Text response with no tool calls."""
    mock_settings.litellm_provider = "ollama"
    mock_settings.ollama_model = "llama3.1:8b"
    mock_settings.ollama_base_url = "http://localhost:11434"
    mock_settings.litellm_timeout = 30
    mock_settings.openai_api_key = ""

    mock_litellm.acompletion = AsyncMock(
        return_value=_make_llm_response(content="Root cause is disk full")
    )

    result = await chat_completion(
        messages=[{"role": "user", "content": "Diagnose this"}],
        tools=[],
    )

    assert result.content == "Root cause is disk full"
    assert result.tool_calls is None
    assert result.error is False
    assert result.usage.prompt_tokens == 10


@pytest.mark.asyncio
@patch("backend.app.core.llm.litellm")
@patch("backend.app.core.llm.settings")
async def test_chat_completion_tool_call_response(
    mock_settings: MagicMock,
    mock_litellm: MagicMock,
) -> None:
    """Response with tool calls is parsed correctly."""
    mock_settings.litellm_provider = "openai"
    mock_settings.openai_model = "gpt-4o"
    mock_settings.litellm_timeout = 30
    mock_settings.openai_api_key = "sk-test"
    mock_settings.ollama_base_url = "http://localhost:11434"

    raw_tc = _make_raw_tool_call(
        call_id="call_abc",
        name="check_disk_usage",
        arguments='{"path": "/var"}',
    )

    mock_litellm.acompletion = AsyncMock(
        return_value=_make_llm_response(
            content=None,
            tool_calls=[raw_tc],
        )
    )

    result = await chat_completion(
        messages=[{"role": "user", "content": "Check disk"}],
        tools=[{"name": "check_disk_usage", "parameters": {}}],
    )

    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "check_disk_usage"
    assert result.tool_calls[0].arguments == {"path": "/var"}
    assert result.error is False


# ── chat_completion: error handling ──────────────────────────────────


@pytest.mark.asyncio
@patch("backend.app.core.llm.litellm")
@patch("backend.app.core.llm.settings")
async def test_chat_completion_timeout_retries_once(
    mock_settings: MagicMock,
    mock_litellm: MagicMock,
) -> None:
    """Timeout triggers one retry, then returns error LLMResponse."""
    mock_settings.litellm_provider = "ollama"
    mock_settings.ollama_model = "llama3.1:8b"
    mock_settings.ollama_base_url = "http://localhost:11434"
    mock_settings.litellm_timeout = 5
    mock_settings.openai_api_key = ""

    mock_litellm.acompletion = AsyncMock(
        side_effect=LiteLLMTimeout(
            message="timed out",
            model="ollama/llama3.1:8b",
            llm_provider="ollama",
        ),
    )

    result = await chat_completion(
        messages=[{"role": "user", "content": "test"}],
    )

    assert result.error is True
    assert "LLM_ERROR" in (result.content or "")
    # Should have been called exactly 2 times (initial + 1 retry)
    assert mock_litellm.acompletion.call_count == 2


@pytest.mark.asyncio
@patch("backend.app.core.llm.litellm")
@patch("backend.app.core.llm.settings")
async def test_chat_completion_api_error_no_retry(
    mock_settings: MagicMock,
    mock_litellm: MagicMock,
) -> None:
    """Non-transient APIError breaks immediately without retry."""
    mock_settings.litellm_provider = "openai"
    mock_settings.openai_model = "gpt-4o"
    mock_settings.litellm_timeout = 30
    mock_settings.openai_api_key = "sk-test"
    mock_settings.ollama_base_url = "http://localhost:11434"

    mock_litellm.acompletion = AsyncMock(
        side_effect=LiteLLMAPIError(
            message="invalid model",
            status_code=400,
            model="gpt-4o",
            llm_provider="openai",
        ),
    )

    result = await chat_completion(
        messages=[{"role": "user", "content": "test"}],
    )

    assert result.error is True
    # APIError should NOT retry — only called once
    assert mock_litellm.acompletion.call_count == 1


@pytest.mark.asyncio
@patch("backend.app.core.llm.litellm")
@patch("backend.app.core.llm.settings")
async def test_chat_completion_succeeds_on_retry(
    mock_settings: MagicMock,
    mock_litellm: MagicMock,
) -> None:
    """Transient failure on first attempt, success on retry."""
    mock_settings.litellm_provider = "ollama"
    mock_settings.ollama_model = "llama3.1:8b"
    mock_settings.ollama_base_url = "http://localhost:11434"
    mock_settings.litellm_timeout = 30
    mock_settings.openai_api_key = ""

    mock_litellm.acompletion = AsyncMock(
        side_effect=[
            LiteLLMTimeout(
                message="first attempt timeout",
                model="ollama/llama3.1:8b",
                llm_provider="ollama",
            ),
            _make_llm_response(content="Recovered!"),
        ],
    )

    result = await chat_completion(
        messages=[{"role": "user", "content": "test"}],
    )

    assert result.error is False
    assert result.content == "Recovered!"
    assert mock_litellm.acompletion.call_count == 2


# ── chat_completion: model override ──────────────────────────────────


@pytest.mark.asyncio
@patch("backend.app.core.llm.litellm")
@patch("backend.app.core.llm.settings")
async def test_chat_completion_model_override(
    mock_settings: MagicMock,
    mock_litellm: MagicMock,
) -> None:
    """Explicit model parameter overrides env config."""
    mock_settings.litellm_provider = "ollama"
    mock_settings.ollama_model = "llama3.1:8b"
    mock_settings.ollama_base_url = "http://localhost:11434"
    mock_settings.litellm_timeout = 30
    mock_settings.openai_api_key = ""

    mock_litellm.acompletion = AsyncMock(
        return_value=_make_llm_response(content="Override!"),
    )

    result = await chat_completion(
        messages=[{"role": "user", "content": "test"}],
        model="gpt-4o-mini",
    )

    assert result.model == "gpt-4o-mini"
    call_kwargs = mock_litellm.acompletion.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"


# ── Pydantic model validation ───────────────────────────────────────


def test_tool_call_model() -> None:
    """ToolCall Pydantic model validates correctly."""
    tc = ToolCall(
        id="call_1",
        name="check_memory",
        arguments={"detailed": True},
    )
    assert tc.id == "call_1"
    assert tc.arguments["detailed"] is True


def test_llm_response_model_defaults() -> None:
    """LLMResponse defaults are sensible."""
    resp = LLMResponse(model="gpt-4o")
    assert resp.content is None
    assert resp.tool_calls is None
    assert resp.error is False
    assert resp.usage.total_tokens == 0


def test_token_usage_model() -> None:
    """TokenUsage correctly sums tokens."""
    usage = TokenUsage(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
    )
    assert usage.total_tokens == 150
