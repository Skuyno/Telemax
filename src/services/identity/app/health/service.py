"""Бизнес-логика проверки состояния приложения."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.health.schemas import HealthResponse


async def health_check(db: AsyncSession) -> HealthResponse:
    """Проверить доступность б.д.

    Args:
        db: Асинхронная сессия б.д.

    Returns:
        HealthResponse: Результат проверки.
    """
    await db.execute(text("SELECT 1"))
    return HealthResponse(description="Health Good")
