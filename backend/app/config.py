"""RootCause AI Application Settings."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for RootCause AI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Target VM Settings
    target_host: str = Field(default="192.168.64.2", description="IP address or hostname of target VM")
    target_user: str = Field(default="ubuntu", description="SSH username")
    target_ssh_key: str = Field(default="~/.ssh/id_rsa", description="Path to SSH private key")
    target_password: str | None = Field(default=None, description="Optional SSH password fallback")

    # Database Settings
    database_url: str = Field(
        default="postgresql+asyncpg://rootcause:rootcause@localhost:5432/rootcause_db",
        description="Async SQLAlchemy database connection URL",
    )

    # AI / LLM Settings
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model identifier")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    ollama_model: str = Field(default="llama3.1:8b", description="Ollama local model name")
    litellm_provider: Literal["openai", "ollama"] = Field(
        default="ollama", description="Active LLM provider route"
    )

    # Reasoning Engine Settings
    max_tool_iterations: int = Field(default=15, description="Max diagnostic tool calls per run")
    diagnosis_timeout_seconds: int = Field(default=120, description="Max diagnosis execution time in seconds")
    max_output_length: int = Field(default=2000, description="Max tool stdout character length before truncation")

    # App Settings
    app_env: Literal["development", "production", "testing"] = Field(default="development")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="DEBUG")


# Singleton instance
settings = Settings()
