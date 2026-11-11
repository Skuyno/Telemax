"""Business logic for pinning/unpinning messages within a chat.

Three effective states per (message, viewer): not pinned, personally
pinned (visible only to this viewer), or pinned chat-wide (visible to
every chat member). A personal "hidden" override lets one viewer drop a
chat-wide pin from their own pinned list without affecting anyone else —
see app/pins/models.py for the two tables backing this.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import repository as chats_repository
from app.chats.models import Message
from app.chats.service import (
    SUBJECT_CHAT_SYNC_REQUIRED,
    SUBJECT_MESSAGE_CREATED,
    build_message_created_payload,
)
from app.events import nats_client
from app.pins import repository as pins_repository


async def _require_membership(db: AsyncSession, chat_id: UUID, user_id: UUID) -> None:
    """Raise if the user is not a member of the chat.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    if not await chats_repository.is_user_in_chat(db, chat_id, user_id):
        raise HTTPException(status_code=403, detail="not a user chat")


async def _get_pinnable_message(
    db: AsyncSession, chat_id: UUID, message_id: UUID
) -> Message:
    """Fetch a message, raising if it doesn't exist or was deleted.

    Args:
        db: Async database session.
        chat_id: Id of the chat the message must belong to.
        message_id: Id of the message.

    Returns:
        Message: The message.

    Raises:
        HTTPException: 404 if the message doesn't exist in this chat or was
            already deleted.
    """
    message = await chats_repository.get_message(db, chat_id, message_id)
    if message is None or message.is_deleted:
        raise HTTPException(status_code=404, detail="message not found")
    return message


async def _notify_chat_sync(db: AsyncSession, chat_id: UUID, reason: str) -> None:
    """Tell every member of the chat to refetch its pinned messages.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        reason: Short machine-readable reason for the refresh.
    """
    members = await chats_repository.list_chat_members(db, chat_id)
    await nats_client.publish(
        SUBJECT_CHAT_SYNC_REQUIRED,
        {
            "chat_id": str(chat_id),
            "reason": reason,
            "recipient_ids": [str(member.user_id) for member in members],
        },
    )


async def _create_pin_service_message(
    db: AsyncSession, chat_id: UUID, target_message_id: UUID, user_id: UUID
) -> None:
    """Add a "message pinned" service message to the chat's history.

    Not idempotency-keyed (client_msg_id=None) on purpose — every
    chat-wide pin is a distinct, real event worth its own history entry,
    including re-pinning the same message after an unpin.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        target_message_id: Id of the message that was pinned.
        user_id: Id of the user who pinned it.
    """
    msg, _ = await chats_repository.create_message(
        db,
        chat_id,
        user_id,
        "Сообщение закреплено.",
        None,
        kind="service",
        service_action="message_pinned",
        service_target_message_id=target_message_id,
    )
    await db.commit()

    members = await chats_repository.list_chat_members(db, chat_id)
    recipient_ids = [str(member.user_id) for member in members]
    await nats_client.publish(
        SUBJECT_MESSAGE_CREATED,
        build_message_created_payload(msg, recipient_ids, []),
    )


async def pin_message(
    db: AsyncSession, chat_id: UUID, message_id: UUID, user_id: UUID, scope: str
) -> None:
    """Pin a message for the caller only, or chat-wide for everyone.

    Any chat member may pin any message in the chat, for either scope.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        message_id: Id of the message to pin.
        user_id: Id of the user requesting the pin.
        scope: "me" for a personal-only pin, "everyone" for a chat-wide one.

    Raises:
        HTTPException: 403 if the user is not a member of the chat, 404 if
            the message doesn't exist or was deleted.
    """
    await _require_membership(db, chat_id, user_id)
    await _get_pinnable_message(db, chat_id, message_id)

    if scope == "everyone":
        if await pins_repository.get_global_pin(db, chat_id, message_id) is None:
            await pins_repository.create_global_pin(db, chat_id, message_id, user_id)
            await _create_pin_service_message(db, chat_id, message_id, user_id)
            await _notify_chat_sync(db, chat_id, "message_pinned")
        return

    # scope == "me"
    if await pins_repository.get_global_pin(db, chat_id, message_id) is not None:
        # Already visible to everyone, including this user — just clear a
        # stale "hidden" override that would otherwise keep suppressing it.
        override = await pins_repository.get_override(db, user_id, message_id)
        if override is not None and override.state == "hidden":
            await pins_repository.delete_override(db, user_id, message_id)
        return

    await pins_repository.upsert_override(
        db, user_id, chat_id, message_id, "personal_pin"
    )


async def unpin_message(
    db: AsyncSession, chat_id: UUID, message_id: UUID, user_id: UUID, scope: str
) -> None:
    """Unpin a message for the caller only, or chat-wide for everyone.

    Unpinning "for me" when a message is pinned chat-wide only hides it
    from the caller's own pinned list — it stays pinned for everyone else.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        message_id: Id of the message to unpin.
        user_id: Id of the user requesting the unpin.
        scope: "me" to only affect the caller, "everyone" to remove the
            chat-wide pin entirely.

    Raises:
        HTTPException: 403 if the user is not a member of the chat, 404 if
            the message doesn't exist or was deleted.
    """
    await _require_membership(db, chat_id, user_id)
    await _get_pinnable_message(db, chat_id, message_id)

    if scope == "everyone":
        await pins_repository.delete_global_pin(db, chat_id, message_id)
        await _notify_chat_sync(db, chat_id, "message_unpinned")
        return

    # scope == "me"
    override = await pins_repository.get_override(db, user_id, message_id)
    if override is not None and override.state == "personal_pin":
        await pins_repository.delete_override(db, user_id, message_id)
        return

    if await pins_repository.get_global_pin(db, chat_id, message_id) is not None:
        await pins_repository.upsert_override(
            db, user_id, chat_id, message_id, "hidden"
        )


async def list_pinned_messages(
    db: AsyncSession, chat_id: UUID, user_id: UUID
) -> list[tuple[Message, bool]]:
    """List messages currently pinned for this user in a chat.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user.

    Returns:
        list[tuple[Message, bool]]: (message, is_global) pairs, newest
            first — `is_global` tells the caller whether this is a
            chat-wide pin or a personal-only one.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    await _require_membership(db, chat_id, user_id)
    pin_rows = await pins_repository.list_pinned_messages_for_user(db, chat_id, user_id)
    if not pin_rows:
        return []

    is_global_by_id = dict(pin_rows)
    messages = await chats_repository.get_messages_by_ids(db, list(is_global_by_id))
    messages.sort(key=lambda m: m.created_at, reverse=True)
    return [(message, is_global_by_id[message.id]) for message in messages]
