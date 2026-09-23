"""Data access layer for user settings."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.models import UserSettings


async def get_by_user_id(db: AsyncSession, user_id: UUID) -> UserSettings | None:
    """Get a user's settings row by user id.

    Args:
        db: Async database session.
        user_id: User's id.

    Returns:
        UserSettings | None: The settings row if it exists, otherwise None.
    """
    return await db.get(UserSettings, user_id)


async def create_default(db: AsyncSession, user_id: UUID) -> UserSettings:
    """Create a settings row with default values for a user.

    Args:
        db: Async database session.
        user_id: User's id.

    Returns:
        UserSettings: The created settings row.
    """
    settings = UserSettings(user_id=user_id)
    db.add(settings)
    await db.commit()
    return settings


async def update_user_settings(
    db: AsyncSession, settings: UserSettings, patch: dict[str, Any]
) -> UserSettings:
    """Apply a partial update to a settings row.

    Args:
        db: Async database session.
        settings: The settings row to update.
        patch: Fields to update, already filtered to explicitly set values.

    Returns:
        UserSettings: The updated settings row.
    """
    for field, value in patch.items():
        setattr(settings, field, value)
    await db.commit()
    return settings
