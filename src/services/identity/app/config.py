"""Configuration module for identity service."""

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
    """Provide a settings object from .env."""

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    seaweedfs_filer_url: str = "http://seaweedfs:8888"
    max_avatar_size_bytes: int = 5_242_880
    # Off by default — logs raw SQL with bound parameter values (emails,
    # password hashes included). Opt in locally via .env when debugging.
    sql_echo: bool = False
    # On by default (current behavior). Set false on a production deploy
    # with invite-only/pre-provisioned accounts — mirrors the frontend's
    # NUXT_PUBLIC_AUTH_NEW_USER, but enforced here too: hiding the button
    # on the frontend alone wouldn't stop a direct POST /auth/register.
    allow_registration: bool = True
    # The one "superuser" account is auto-provisioned on startup if no
    # superuser exists yet, using these credentials — change them via env
    # before a real deploy, the defaults are for local dev only.
    superuser_username: str = "admin"
    superuser_password: str = "admin123"

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
