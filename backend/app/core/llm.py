"""LiteLLM abstraction layer for provider-agnostic LLM routing.

Routes between OpenAI (GPT-4o) and Ollama (llama3.1:8b) based on
the LITELLM_PROVIDER environment variable. All LLM calls in the
application go through this single module.

SECURITY: This module never logs, stores, or returns the system prompt.
"""

import json
import logging
from typing import Any

import litellm
from litellm.exceptions import (
    APIConnectionError as LiteLLMConnectionError,
)
from litellm.exceptions import (
    APIError as LiteLLMAPIError,
)
from litellm.exceptions import (
    RateLimitError as LiteLLMRateLimitError,
)
from litellm.exceptions import (
    Timeout as LiteLLMTimeout,
)
from pydantic import BaseModel, Field

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Suppress LiteLLM's verbose default logging
litellm.suppress_debug_info = True


class TokenUsage(BaseModel):
    """Token consumption for cost tracking."""

    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)


class ToolCall(BaseModel):
    """A single tool invocation requested by the LLM."""

    id: str = Field(description="Unique call ID for correlating results")
    name: str = Field(description="Tool function name")
    arguments: dict[str, Any] = Field(
        description="Parsed JSON arguments for the tool",
    )


class LLMResponse(BaseModel):
    """Structured response from any LLM provider."""

    content: str | None = Field(
        default=None,
        description="Text response (final diagnosis or reasoning)",
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None,
        description="Function calls the LLM wants to execute",
    )
    model: str = Field(description="Model that produced this response")
    usage: TokenUsage = Field(default_factory=TokenUsage)
    error: bool = Field(
        default=False,
        description="True if this response represents an error",
    )


def _resolve_model_name() -> str:
    """Build the LiteLLM-compatible model identifier.

    LiteLLM requires Ollama models to be prefixed with 'ollama/'
    while OpenAI models are passed as-is.
    """
    if settings.litellm_provider == "ollama":
        return f"ollama/{settings.ollama_model}"
    return settings.openai_model


def _parse_tool_calls(
    raw_tool_calls: list[Any],
) -> list[ToolCall]:
    """Parse raw LiteLLM tool call objects into typed ToolCall models."""
    parsed: list[ToolCall] = []

    for tc in raw_tool_calls:
        try:
            func = tc.function
            # Arguments come as a JSON string — parse to dict
            args_str = func.arguments
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}
                logger.warning(
                    "Failed to parse tool call arguments: %s",
                    args_str,
                )

            parsed.append(
                ToolCall(
                    id=tc.id or "",
                    name=func.name,
                    arguments=args,
                )
            )
        except AttributeError:
            logger.warning("Malformed tool call object: %s", tc)
            continue

    return parsed


def _extract_usage(raw_usage: Any) -> TokenUsage:
    """Extract token usage from LiteLLM response."""
    if raw_usage is None:
        return TokenUsage()

    return TokenUsage(
        prompt_tokens=getattr(raw_usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(raw_usage, "completion_tokens", 0) or 0,
        total_tokens=getattr(raw_usage, "total_tokens", 0) or 0,
    )


async def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> LLMResponse:
    """Send a chat completion request through LiteLLM.

    Args:
        messages: OpenAI-format message list (system, user, assistant, tool).
        tools: OpenAI function-calling tool definitions.
        model: Override model name. Defaults to env-configured provider.

    Returns:
        LLMResponse with either tool_calls or content populated.
        On failure after one retry, returns an error LLMResponse
        (error=True, content describes the failure). Never raises.
    """
    resolved_model = model or _resolve_model_name()

    # Build kwargs for litellm.acompletion
    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "timeout": settings.litellm_timeout,
    }

    # Only include tools if provided and non-empty
    if tools:
        kwargs["tools"] = [
            {"type": "function", "function": t} for t in tools
        ]

    # Set Ollama-specific base URL
    if settings.litellm_provider == "ollama":
        kwargs["api_base"] = settings.ollama_base_url

    # Set OpenAI API key
    if settings.litellm_provider == "openai" and settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key

    # Attempt with one retry on transient failure
    last_error: str = ""
    for attempt in range(2):
        try:
            response = await litellm.acompletion(**kwargs)

            # Extract the first choice
            choice = response.choices[0]
            message = choice.message

            # Parse tool calls if present
            tool_calls: list[ToolCall] | None = None
            if message.tool_calls:
                tool_calls = _parse_tool_calls(message.tool_calls)

            # Extract text content
            content = message.content

            return LLMResponse(
                content=content,
                tool_calls=tool_calls if tool_calls else None,
                model=resolved_model,
                usage=_extract_usage(response.usage),
            )

        except LiteLLMTimeout:
            last_error = (
                f"LLM request timed out after {settings.litellm_timeout}s "
                f"(attempt {attempt + 1}/2)"
            )
            logger.warning(last_error)

        except LiteLLMRateLimitError:
            last_error = f"Rate limited by {resolved_model} (attempt {attempt + 1}/2)"
            logger.warning(last_error)

        except LiteLLMConnectionError as err:
            last_error = f"Cannot reach LLM provider: {err} (attempt {attempt + 1}/2)"
            logger.warning(last_error)

        except LiteLLMAPIError as err:
            last_error = f"LLM API error: {err} (attempt {attempt + 1}/2)"
            logger.warning(last_error)
            # Non-transient API errors — don't retry
            break

    # Both attempts failed — return structured error
    logger.error("LLM call failed after retries: %s", last_error)
    return LLMResponse(
        content=f"LLM_ERROR: {last_error}",
        tool_calls=None,
        model=resolved_model,
        usage=TokenUsage(),
        error=True,
    )
