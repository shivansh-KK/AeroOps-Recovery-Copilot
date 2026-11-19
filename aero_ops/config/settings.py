"""Typed application settings and aviation operating limits."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AeroOps"
    model_provider: str = Field(default="mock", description="mock, openai, anthropic, or gemini")
    model_name: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    database_path: Path = Path("aero_ops.db")
    minimum_connection_minutes: int = 60
    standard_max_duty_hours: float = 14.0
    maximum_agent_steps: int = 12
    max_retries: int = 3
    default_runway_heading_degrees: float = 340.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
