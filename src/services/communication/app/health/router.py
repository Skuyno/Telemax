"""Health check routes for the application and database."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db
from app.health import service as health_service
from app.health.schemas import HealthResponse

router = APIRouter()


@router.get("/health/db", response_model=HealthResponse, tags=["Health"])
async def health_db(db: AsyncSession = Depends(get_async_db)):
    """Check database health.

    Args:
        db: Async database session.

    Returns:
        HealthResponse: Check result.
    """
    return await health_service.health_check(db)
