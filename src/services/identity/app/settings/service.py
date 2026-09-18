"""Business logic for user settings."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import repository as settings_repository
from app.settings.models import UserSettings
from app.settings.schemas import UserSettingsUpdateRequest


async def get_or_create_settings(db: AsyncSession, user_id: UUID) -> UserSettings:
    """Get a user's settings, creating a default row on first access.

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


async def update_settings(
    db: AsyncSession, user_id: UUID, data: UserSettingsUpdateRequest
) -> UserSettings:
    """Apply a partial update to a user's settings.

    Args:
        db: Async database session.
        user_id: User's id.
        data: Fields to update; fields left unset are unchanged.

    Returns:
        UserSettings: The updated settings.
    """
    settings = await get_or_create_settings(db, user_id)
    patch = data.model_dump(exclude_unset=True)
    return await settings_repository.update(db, settings, patch)
