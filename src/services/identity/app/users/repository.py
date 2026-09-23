"""Data access layer for users."""

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import or_, select
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


async def update_user(db: AsyncSession, user: User, patch: dict[str, Any]) -> User:
    """Apply a partial update to a user row.

    Args:
        db: Async database session.
        user: The user row to update.
        patch: Fields to update, already filtered to explicitly set values.

    Returns:
        User: The updated user.
    """
    for field, value in patch.items():
        setattr(user, field, value)
    await db.commit()
    return user


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


async def search_users(
    db: AsyncSession,
    *,
    tag: str | None,
    email: str | None,
    phone: str | None,
    name: str | None,
    query: str | None,
    limit: int,
) -> Sequence[User]:
    """Search users by tag prefix and/or substring match on other fields.

    All matching is case-insensitive (`ILIKE`). Every given field must
    match (logical AND); `query` matches if email, phone, or display_name
    contains it (logical OR among those three).

    Args:
        db: Async database session.
        tag: Prefix to match against username; caller strips any leading "@".
        email: Substring to match against email.
        phone: Substring to match against phone.
        name: Substring to match against display_name.
        query: Substring to match against email, phone, or display_name.
        limit: Maximum number of rows to return.

    Returns:
        Sequence[User]: Matching users ordered by username, capped at limit.
    """
    conditions = []
    if tag:
        conditions.append(User.username.ilike(f"{tag}%"))
    if email:
        conditions.append(User.email.ilike(f"%{email}%"))
    if phone:
        conditions.append(User.phone.ilike(f"%{phone}%"))
    if name:
        conditions.append(User.display_name.ilike(f"%{name}%"))
    if query:
        pattern = f"%{query}%"
        conditions.append(
            or_(
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
                User.display_name.ilike(pattern),
            )
        )

    stmt = select(User).where(*conditions).order_by(User.username).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
