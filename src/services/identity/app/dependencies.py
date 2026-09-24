"""FastAPI dependencies."""

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.users.models import User


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


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """Load the calling user's row, needed to check its role.

    Args:
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        User: The calling user's row.

    Raises:
        HTTPException: 401 if the token is for a user that no longer
            exists (e.g. their account was deleted after it was issued).
    """
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles: str):
    """Build a dependency that only lets callers with one of `roles` through.

    Args:
        roles: Role names allowed to proceed.

    Returns:
        A FastAPI dependency yielding the caller's User row.
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _check
