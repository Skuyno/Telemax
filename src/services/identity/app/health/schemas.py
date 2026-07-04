"""Pydantic-схемы для проверки состояния."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Базовый ответ."""

    description: str
