"""Data access layer for message pins."""

from uuid import UUID

from sqlalchemy import delete, literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.pins.models import ChatMessagePin, MessagePinOverride


async def get_global_pin(
    db: AsyncSession, chat_id: UUID, message_id: UUID
) -> ChatMessagePin | None:
    """Get a message's chat-wide pin row, if it's pinned for everyone.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        message_id: Id of the message.

    Returns:
        ChatMessagePin | None: The pin row if it exists, otherwise None.
    """
    return await db.get(ChatMessagePin, {"chat_id": chat_id, "message_id": message_id})


async def create_global_pin(
    db: AsyncSession, chat_id: UUID, message_id: UUID, pinned_by: UUID
) -> ChatMessagePin:
    """Pin a message chat-wide.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        message_id: Id of the message.
        pinned_by: Id of the user who pinned it.

    Returns:
        ChatMessagePin: The created pin row.
    """
    pin = ChatMessagePin(chat_id=chat_id, message_id=message_id, pinned_by=pinned_by)
    db.add(pin)
    await db.commit()
    return pin


async def delete_global_pin(db: AsyncSession, chat_id: UUID, message_id: UUID) -> None:
    """Unpin a message chat-wide. A no-op if it wasn't pinned.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        message_id: Id of the message.
    """
    await db.execute(
        delete(ChatMessagePin).where(
            ChatMessagePin.chat_id == chat_id,
            ChatMessagePin.message_id == message_id,
        )
    )
    await db.commit()


async def get_override(
    db: AsyncSession, user_id: UUID, message_id: UUID
) -> MessagePinOverride | None:
    """Get a user's personal override for a message, if any.

    Args:
        db: Async database session.
        user_id: Id of the user.
        message_id: Id of the message.

    Returns:
        MessagePinOverride | None: The override row if it exists.
    """
    return await db.get(
        MessagePinOverride, {"user_id": user_id, "message_id": message_id}
    )


async def upsert_override(
    db: AsyncSession, user_id: UUID, chat_id: UUID, message_id: UUID, state: str
) -> None:
    """Create or replace a user's personal override for a message.

    Args:
        db: Async database session.
        user_id: Id of the user.
        chat_id: Id of the chat the message belongs to.
        message_id: Id of the message.
        state: Either "personal_pin" or "hidden".
    """
    statement = (
        pg_insert(MessagePinOverride)
        .values(
            user_id=user_id, chat_id=chat_id, message_id=message_id, state=state
        )
        .on_conflict_do_update(
            index_elements=["user_id", "message_id"],
            set_={"state": state},
        )
    )
    await db.execute(statement)
    await db.commit()


async def delete_override(db: AsyncSession, user_id: UUID, message_id: UUID) -> None:
    """Remove a user's personal override for a message, if any.

    Args:
        db: Async database session.
        user_id: Id of the user.
        message_id: Id of the message.
    """
    await db.execute(
        delete(MessagePinOverride).where(
            MessagePinOverride.user_id == user_id,
            MessagePinOverride.message_id == message_id,
        )
    )
    await db.commit()


async def list_pinned_messages_for_user(
    db: AsyncSession, chat_id: UUID, user_id: UUID
) -> list[tuple[UUID, bool]]:
    """Get a user's effective pinned message ids in a chat.

    A message counts as pinned for this user if it's pinned chat-wide and
    this user hasn't personally hidden it, or if this user has personally
    pinned it (regardless of its chat-wide state).

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user.

    Returns:
        list[tuple[UUID, bool]]: (message_id, is_global) pairs — `is_global`
            tells the caller whether this is a chat-wide pin (True) or a
            personal-only one (False).
    """
    hidden_ids = select(MessagePinOverride.message_id).where(
        MessagePinOverride.user_id == user_id,
        MessagePinOverride.state == "hidden",
    )
    global_rows = select(
        ChatMessagePin.message_id, literal(True).label("is_global")
    ).where(
        ChatMessagePin.chat_id == chat_id,
        ChatMessagePin.message_id.not_in(hidden_ids),
    )
    personal_rows = select(
        MessagePinOverride.message_id, literal(False).label("is_global")
    ).where(
        MessagePinOverride.chat_id == chat_id,
        MessagePinOverride.user_id == user_id,
        MessagePinOverride.state == "personal_pin",
    )
    result = await db.execute(global_rows.union(personal_rows))
    return [(row[0], row[1]) for row in result.all()]
