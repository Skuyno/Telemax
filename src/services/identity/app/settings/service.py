"""Business logic for user settings."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import repository as settings_repository
from app.settings.models import UserSettings
from app.settings.schemas import UserSettingsUpdateRequest


async def _fetch_or_create(db: AsyncSession, user_id: UUID) -> UserSettings:
    """Fetch a user's settings row, creating one with defaults on first access.

    Args:
        db: Async database session.
        user_id: User's id.

    Returns:
        UserSettings: The user's settings.
    """
    settings = await settings_repository.get_by_user_id(db, user_id)
    if settings is None:
        settings = await settings_repository.create_default(db, user_id)
    return settings


async def get_or_create_settings(db: AsyncSession, user_id: UUID) -> UserSettings:
    """Get a user's settings, creating a default row on first access.

    Args:
        db: Async database session.
        user_id: User's id.

    Returns:
        UserSettings: The user's settings.
    """
    return await _fetch_or_create(db, user_id)


async def update_settings(
    db: AsyncSession, user_id: UUID, data: UserSettingsUpdateRequest
) -> UserSettings:
    """Apply a partial update to a user's settings.

    A settings row must exist before it can be patched, so this ensures one
    (creating defaults on first write) rather than reusing the read path.

    Args:
        db: Async database session.
        user_id: User's id.
        data: Fields to update; fields left unset are unchanged.

    Returns:
        UserSettings: The updated settings.
    """
    settings = await _fetch_or_create(db, user_id)
    patch = data.model_dump(exclude_unset=True)
    return await settings_repository.update_user_settings(db, settings, patch)
