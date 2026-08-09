"""Configuration module for communication service."""

from pathlib import Path

from pydantic import computed_field
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

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    identity_url: str = "http://identity:8000"
    nats_port: int = 4222

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        """Build the database connection URL.

        Returns:
            str: PostgreSQL connection URL.
        """
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()
