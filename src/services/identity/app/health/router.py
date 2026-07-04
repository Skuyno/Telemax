"""Роуты проверки состояния приложения и б.д."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db
from app.health import service as health_service
from app.health.schemas import HealthResponse

router = APIRouter()


@router.get("/health/db", response_model=HealthResponse, tags=["Здоровье"])
async def health_db(db: AsyncSession = Depends(get_async_db)):
    """Проверить состояние б.д.

    Args:
        db: Асинхронная сессия б.д.

    Returns:
        HealthResponse: Результат проверки.
    """
    return await health_service.health_check(db)
