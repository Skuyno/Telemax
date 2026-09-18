"""Business logic for per-chat settings.

The only touch point with the chats domain is membership validation, done
through `app.chats.repository` rather than a shared table or model, so the
two modules stay independent.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import repository as chats_repository
from app.settings import repository as settings_repository
from app.settings.models import ChatSettings
from app.settings.schemas import ChatSettingsUpdateRequest


async def get_or_create_settings(
    db: AsyncSession, chat_id: UUID, user_id: UUID
) -> ChatSettings:
    """Get a user's settings for a chat, creating a default row on first access.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user requesting their settings.

    Returns:
        ChatSettings: The user's settings for the chat.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    if not await chats_repository.is_user_in_chat(db, chat_id, user_id):
        raise HTTPException(status_code=403, detail="not a user chat")

    settings = await settings_repository.get(db, chat_id, user_id)
    if settings is None:
        settings = await settings_repository.create_default(db, chat_id, user_id)
    return settings


async def update_settings(
    db: AsyncSession,
    chat_id: UUID,
    user_id: UUID,
    data: ChatSettingsUpdateRequest,
) -> ChatSettings:
    """Apply a partial update to a user's settings for a chat.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user updating their settings.
        data: Fields to update; fields left unset are unchanged.

    Returns:
        ChatSettings: The updated settings.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    settings = await get_or_create_settings(db, chat_id, user_id)
    patch = data.model_dump(exclude_unset=True)
    return await settings_repository.update(db, settings, patch)
