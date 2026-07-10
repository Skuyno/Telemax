"""Configuration module for api-gateway service."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> Path | None:
    """Locate the .env file in the project.

    Returns:
        Path | None: Path to the .env file if found, otherwise None.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "deploy" / ".env"
        if candidate.exists():
            return candidate
    return None


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    identity_url: str = "http://identity:8000"
    communication_url: str = "http://communication:8000"

    model_config = SettingsConfigDict(
        env_file= _find_env_file(),
        env_file_encoding="utf-8",
    )


settings = Settings()
