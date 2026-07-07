"""Data access layer for users."""
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
