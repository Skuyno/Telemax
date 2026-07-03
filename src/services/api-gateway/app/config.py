from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]

class Settings(BaseSettings):
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    identity_url : str = "http://identity:8000"
    communication_url: str = "http://communication:8000"

    model_config = SettingsConfigDict(
        env_file = REPO_ROOT / "deploy" / ".env",
        env_file_encoding = "utf-8",
    )
    