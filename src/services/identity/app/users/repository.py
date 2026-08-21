"""Data access layer for users."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User


async def create_user(db: AsyncSession, username: str, password_hash: str) -> User:
    """Create a user row.

    Args:
        db: Async database session.
        username: Unique login name.
        password_hash: Argon2 hash of the password.

    Returns:
        User: The persisted user.
    """
    user = User(username=username, password_hash=password_hash)
    db.add(user)
    await db.commit()
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get a user by username.

    Args:
        db: Async database session.
        username: Unique login name.

    Returns:
        User | None: The user if found, otherwise None.
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get a user by primary key.

    Args:
        db: Async database session.
        user_id: User's id.

    Returns:
        User | None: The user if found, otherwise None.
    """
    return await db.get(User, user_id)


async def get_users_bulk(db: AsyncSession, user_ids: set[UUID]) -> Sequence[User]:
    """Fetch all users whose id is in the given set.

    Args:
        db: Async database session.
        user_ids: Set of user ids to look up.

    Returns:
        Sequence[User]: Matching users; ids not present in the table
        are silently skipped.
    """
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return result.scalars().all()
