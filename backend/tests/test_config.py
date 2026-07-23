"""Unit tests for backend application configuration."""

import pytest

from backend.app.config import Settings


def test_default_settings() -> None:
    """Test default values when no env variables override them."""
    cfg = Settings()
    assert cfg.target_user == "ubuntu"
    assert cfg.max_tool_iterations == 15
    assert cfg.max_output_length == 2000
    assert cfg.litellm_provider in ("openai", "ollama")


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test environment variable override functionality."""
    monkeypatch.setenv("TARGET_HOST", "10.0.0.5")
    monkeypatch.setenv("MAX_TOOL_ITERATIONS", "10")
    monkeypatch.setenv("LITELLM_PROVIDER", "openai")

    cfg = Settings()
    assert cfg.target_host == "10.0.0.5"
    assert cfg.max_tool_iterations == 10
    assert cfg.litellm_provider == "openai"
