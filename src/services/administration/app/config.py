"""Configuration module for administration service."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> Path | None:
    """Locate the .env file in the project.

    Returns:
        Path | None: Path to the .env file if found, otherwise None.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return None


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    identity_url: str = "http://identity:8000"

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
    )


settings = Settings()
