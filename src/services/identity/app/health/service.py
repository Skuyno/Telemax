"""Health check business logic."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.health.schemas import HealthResponse


async def health_check(db: AsyncSession) -> HealthResponse:
    """Check database availability.

    Args:
        db: Async database session.

    Returns:
        HealthResponse: Check result.
    """
    await db.execute(text("SELECT 1"))
    return HealthResponse(description="Health Good")
