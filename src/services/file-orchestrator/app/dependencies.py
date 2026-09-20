"""FastAPI dependencies."""

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session.

    Yields:
        AsyncSession: Async database session.
    """
    async with async_session_maker() as session:
        yield session


async def get_current_user_id(x_user_id: UUID = Header(...)) -> UUID:
    """Trust the user id set by API Gateway."""
    return x_user_id
