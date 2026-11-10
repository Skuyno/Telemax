"""Data access layer for per-chat settings."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.models import ChatSettings


async def get_chat_settings(
    db: AsyncSession, chat_id: UUID, user_id: UUID
) -> ChatSettings | None:
    """Get a user's settings row for a chat.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user.

    Returns:
        ChatSettings | None: The settings row if it exists, otherwise None.
    """
    return await db.get(ChatSettings, {"chat_id": chat_id, "user_id": user_id})


async def create_default(
    db: AsyncSession, chat_id: UUID, user_id: UUID
) -> ChatSettings:
    """Create a settings row with default values for a user in a chat.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user.

    Returns:
        ChatSettings: The created settings row.
    """
    settings = ChatSettings(chat_id=chat_id, user_id=user_id)
    db.add(settings)
    await db.commit()
    return settings


async def update_chat_settings(
    db: AsyncSession, settings: ChatSettings, patch: dict[str, Any]
) -> ChatSettings:
    """Apply a partial update to a settings row.

    Args:
        db: Async database session.
        settings: The settings row to update.
        patch: Fields to update, already filtered to explicitly set values.

    Returns:
        ChatSettings: The updated settings row.
    """
    for field, value in patch.items():
        setattr(settings, field, value)
    await db.commit()
    return settings


async def list_pinned_chat_ids(db: AsyncSession, user_id: UUID) -> dict[UUID, datetime]:
    """Get the chats this user has pinned, with when each was pinned.

    Args:
        db: Async database session.
        user_id: Id of the user.

    Returns:
        dict[UUID, datetime]: `pinned_at` per pinned chat id.
    """
    result = await db.execute(
        select(ChatSettings.chat_id, ChatSettings.pinned_at).where(
            ChatSettings.user_id == user_id,
            ChatSettings.is_pinned.is_(True),
        )
    )
    return dict(result.all())
