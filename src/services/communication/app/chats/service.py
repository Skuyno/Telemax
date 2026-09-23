"""Business logic for chats."""

from typing import Sequence
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import repository as chats_repository
from app.chats.models import Chat, ChatMember, Message
from app.chats.schemas import CreateDirectChatRequest, SendMessageRequest
from app.config import settings
from app.events import nats_client

SUBJECT_MESSAGE_CREATED = "chat.message.created"
SUBJECT_MESSAGE_UPDATED = "chat.message.updated"
SUBJECT_MESSAGE_DELETED = "chat.message.deleted"
SUBJECT_MESSAGE_READ = "chat.message.read"
SUBJECT_TYPING = "chat.message.typing"


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


async def _get_recipient_ids(
    db: AsyncSession, chat_id: UUID, exclude_user_id: UUID | None = None
) -> list[str]:
    """List chat member ids as strings, optionally excluding one user.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        exclude_user_id: If given, this user's id is left out of the result.

    Returns:
        list[str]: Member ids as strings, suitable for a NATS event payload.
    """
    members = await chats_repository.list_chat_members(db, chat_id)
    return [str(m.user_id) for m in members if m.user_id != exclude_user_id]


async def _validate_attachments(
    chat_id: UUID, file_ids: Sequence[UUID]
) -> None:
    """Verify a set of file ids are ready and belong to this chat.

    Delegates to file-orchestrator, the source of truth for files — this
    service only stores the association, not the files themselves.

    Args:
        chat_id: Id of the chat the message is being sent to.
        file_ids: Ids of files the client wants to attach.

    Raises:
        HTTPException: 400 if any file id isn't a ready, valid attachment
            for this chat.
    """
    if not file_ids:
        return

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.file_orchestrator_url}/internal/files/validate",
            json={"chat_id": str(chat_id), "file_ids": [str(fid) for fid in file_ids]},
        )
    response.raise_for_status()
    valid_ids = {UUID(fid) for fid in response.json()["valid_file_ids"]}

    if not set(file_ids).issubset(valid_ids):
        raise HTTPException(status_code=400, detail="invalid attachment file id")


async def get_or_create_direct_chat(
    db: AsyncSession, user_id: UUID, data: CreateDirectChatRequest
) -> tuple[Chat, bool]:
    """Get an existing direct chat with the peer or create a new one.

    Args:
        db: Async database session.
        user_id: Id of the user making the request.
        data: Request body with the peer's user id.

    Returns:
        tuple[Chat, bool]: The chat and True if it was created,
        False if it already existed.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.identity_url}/internal/users/{data.peer_user_id}"
        )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="peer user not found")

    try:
        return (
            await chats_repository.create_direct_chat(
                db, creator_id=user_id, peer_id=data.peer_user_id
            ),
            True,
        )
    except IntegrityError:
        chat = await chats_repository.get_direct_chat(
            db, user_a=user_id, user_b=data.peer_user_id
        )
        if chat is None:
            raise
        return chat, False


async def list_user_chats(db: AsyncSession, user_id: UUID) -> Sequence[Chat]:
    """List all chats the given user is a member of.

    Args:
        db: Async database session.
        user_id: Id of the user to look up chats for.

    Returns:
        Sequence[Chat]: All chat the user is a member of.
    """
    return await chats_repository.list_user_chats(db, user_id)


async def get_last_messages(
    db: AsyncSession, chat_ids: Sequence[UUID]
) -> dict[UUID, Message]:
    """Look up the most recent message for each of the given chats.

    Args:
        db: Async database session.
        chat_ids: Chats to look up the last message for.

    Returns:
        dict[UUID, Message]: Latest message per chat id.
    """
    return await chats_repository.get_last_messages(db, chat_ids)


async def list_chat_members(
    db: AsyncSession, chat_id: UUID, user_id: UUID
) -> Sequence[ChatMember]:
    """Get members of a chat, verifying the user's access.

    Args:
        db: Async database session.
        chat_id: Id of the chat to look up.
        user_id: Id of the user requesting the members.

    Returns:
        Sequence[ChatMember]: A list of chat members.

    Raises:
        HTTPException: 403 if the user is not a member of the chat,
        or 404 if the chat does not exist.
    """
    await _require_membership(db, chat_id, user_id)
    return await chats_repository.list_chat_members(db, chat_id)


async def send_message(
    db: AsyncSession, chat_id: UUID, user_id: UUID, data: SendMessageRequest
) -> Message:
    """Validate access and save a new message to the database.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the sender.
        data: Message payload.

    Returns:
        Message: The created of existing message.

    Raises:
        HTTPException: 403 if the sender is not a member of the chat.
    """
    await _require_membership(db, chat_id, user_id)
    await _validate_attachments(chat_id, data.attachment_file_ids)

    msg, created = await chats_repository.create_message(
        db, chat_id, user_id, data.body, data.client_msg_id
    )

    if msg.chat_id != chat_id or msg.body != data.body:
        raise HTTPException(
            status_code=409,
            detail="client_msg_id already used for a different chat or message body",
        )

    # Only on first creation: a retried request with the same client_msg_id
    # returns the existing row, and re-inserting the same attachment links
    # would violate their composite primary key.
    if created:
        await chats_repository.add_attachments(db, msg.id, data.attachment_file_ids)

    recipient_ids = await _get_recipient_ids(db, chat_id)

    await nats_client.publish(
        SUBJECT_MESSAGE_CREATED,
        {
            "id": str(msg.id),
            "chat_id": str(msg.chat_id),
            "sender_id": str(msg.sender_id),
            "recipient_ids": recipient_ids,
            "body": msg.body,
            "attachment_file_ids": [str(fid) for fid in data.attachment_file_ids],
            "created_at": msg.created_at.isoformat(),
        },
    )

    return msg


async def get_chat_messages(
    db: AsyncSession,
    chat_id: UUID,
    user_id: UUID,
    limit: int,
    before_msg_id: UUID | None,
) -> list[Message]:
    """Get the message history of a chat, verifying user access.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user requesting the history.
        limit: Max number of messages to return.
        before_msg_id: Optional cursor for pagination.

    Returns:
        list[Message]: Paginated list of messages from newest to oldest.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    await _require_membership(db, chat_id, user_id)
    return await chats_repository.get_chat_messages(db, chat_id, limit, before_msg_id)


async def list_chat_peer_ids(
    db: AsyncSession,
    user_id: UUID,
) -> Sequence[UUID]:
    """Return IDs of users who share a chat with the given user.

    Args:
        db: Async database session.
        user_id: ID of the user whose chat peers should be found.

    Returns:
        Sequence[UUID]: Unique IDs of the user's chat peers.
    """
    return await chats_repository.list_chat_peer_ids(db, user_id)


async def _get_owned_message(
    db: AsyncSession, chat_id: UUID, message_id: UUID, user_id: UUID
) -> Message:
    """Fetch a message and verify the user is its sender.

    Args:
        db: Async database session.
        chat_id: Id of the chat the message belongs to.
        message_id: Id of the message.
        user_id: Id of the user who must be the sender.

    Returns:
        Message: The message.

    Raises:
        HTTPException: 404 if the message doesn't exist in this chat,
            403 if the user isn't its sender or it's already deleted.
    """
    message = await chats_repository.get_message(db, chat_id, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="message not found")
    if message.sender_id != user_id:
        raise HTTPException(status_code=403, detail="not the sender of this message")
    if message.is_deleted:
        raise HTTPException(status_code=403, detail="message already deleted")
    return message


async def edit_message(
    db: AsyncSession, chat_id: UUID, message_id: UUID, user_id: UUID, body: str
) -> Message:
    """Edit a message's text; only the original sender may do this.

    Args:
        db: Async database session.
        chat_id: Id of the chat the message belongs to.
        message_id: Id of the message to edit.
        user_id: Id of the user requesting the edit.
        body: New text content.

    Returns:
        Message: The updated message.

    Raises:
        HTTPException: 403 if the caller isn't the chat member/sender,
            404 if the message doesn't exist.
    """
    await _require_membership(db, chat_id, user_id)
    message = await _get_owned_message(db, chat_id, message_id, user_id)
    message = await chats_repository.update_message_body(db, message, body)

    recipient_ids = await _get_recipient_ids(db, chat_id, exclude_user_id=user_id)
    await nats_client.publish(
        SUBJECT_MESSAGE_UPDATED,
        {
            "id": str(message.id),
            "chat_id": str(message.chat_id),
            "sender_id": str(message.sender_id),
            "recipient_ids": recipient_ids,
            "body": message.body,
            "edited_at": message.edited_at.isoformat() if message.edited_at else None,
            "created_at": message.created_at.isoformat(),
        },
    )
    return message


async def delete_message(
    db: AsyncSession, chat_id: UUID, message_id: UUID, user_id: UUID
) -> Message:
    """Soft-delete a message; only the original sender may do this.

    Args:
        db: Async database session.
        chat_id: Id of the chat the message belongs to.
        message_id: Id of the message to delete.
        user_id: Id of the user requesting the deletion.

    Returns:
        Message: The deleted message (body cleared, `is_deleted` set).

    Raises:
        HTTPException: 403 if the caller isn't the chat member/sender,
            404 if the message doesn't exist.
    """
    await _require_membership(db, chat_id, user_id)
    message = await _get_owned_message(db, chat_id, message_id, user_id)
    attachment_ids = await chats_repository.get_attachment_ids(db, message_id)
    message = await chats_repository.soft_delete_message(db, message)

    recipient_ids = await _get_recipient_ids(db, chat_id, exclude_user_id=user_id)
    await nats_client.publish(
        SUBJECT_MESSAGE_DELETED,
        {
            "id": str(message.id),
            "chat_id": str(message.chat_id),
            "sender_id": str(message.sender_id),
            "recipient_ids": recipient_ids,
            # file-orchestrator subscribes to the same subject to delete the
            # underlying blobs; ws-gateway ignores this field.
            "attachment_file_ids": [str(fid) for fid in attachment_ids],
        },
    )
    return message


async def search_messages(
    db: AsyncSession, chat_id: UUID, user_id: UUID, query: str, limit: int
) -> list[Message]:
    """Search a chat's messages by a case-insensitive substring.

    Args:
        db: Async database session.
        chat_id: Id of the chat to search within.
        user_id: Id of the user performing the search.
        query: Substring to match against message text.
        limit: Maximum number of rows to return.

    Returns:
        list[Message]: Matching messages, newest first.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    await _require_membership(db, chat_id, user_id)
    return await chats_repository.search_messages(db, chat_id, query, limit)


async def send_typing(db: AsyncSession, chat_id: UUID, user_id: UUID) -> None:
    """Notify other chat members that a user is typing.

    Purely ephemeral — nothing is persisted, this just publishes an event
    for `ws-gateway` to relay to whoever is currently connected.

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user who is typing.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    await _require_membership(db, chat_id, user_id)
    recipient_ids = await _get_recipient_ids(db, chat_id, exclude_user_id=user_id)
    await nats_client.publish(
        SUBJECT_TYPING,
        {
            "chat_id": str(chat_id),
            "user_id": str(user_id),
            "recipient_ids": recipient_ids,
        },
    )


async def mark_chat_read(
    db: AsyncSession, chat_id: UUID, user_id: UUID, last_read_message_id: UUID
) -> None:
    """Mark a chat read up to (and including) a given message.

    Notifies the other chat members so their UI can flip read receipts on
    their own sent messages (the "double checkmark" effect).

    Args:
        db: Async database session.
        chat_id: Id of the chat.
        user_id: Id of the user marking it read.
        last_read_message_id: Id of the last message read.

    Raises:
        HTTPException: 403 if the user is not a member of the chat, 404 if
            the message doesn't exist in this chat.
    """
    await _require_membership(db, chat_id, user_id)
    message = await chats_repository.get_message(db, chat_id, last_read_message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="message not found")

    await chats_repository.set_read_state(
        db, chat_id, user_id, last_read_message_id, message.created_at
    )

    recipient_ids = await _get_recipient_ids(db, chat_id, exclude_user_id=user_id)
    await nats_client.publish(
        SUBJECT_MESSAGE_READ,
        {
            "chat_id": str(chat_id),
            "user_id": str(user_id),
            "last_read_message_id": str(last_read_message_id),
            "recipient_ids": recipient_ids,
        },
    )


async def get_attachment_ids(db: AsyncSession, message_id: UUID) -> list[UUID]:
    """Get the attachment file ids for a single message.

    Args:
        db: Async database session.
        message_id: Id of the message.

    Returns:
        list[UUID]: Ids of attached files.
    """
    return await chats_repository.get_attachment_ids(db, message_id)


async def get_attachment_ids_bulk(
    db: AsyncSession, message_ids: Sequence[UUID]
) -> dict[UUID, list[UUID]]:
    """Get attachment file ids for a batch of messages.

    Args:
        db: Async database session.
        message_ids: Ids of messages to look up attachments for.

    Returns:
        dict[UUID, list[UUID]]: Attachment file ids per message id.
    """
    return await chats_repository.get_attachment_ids_bulk(db, message_ids)


async def get_unread_counts(
    db: AsyncSession, user_id: UUID, chat_ids: Sequence[UUID]
) -> dict[UUID, int]:
    """Get unread message counts for a batch of chats.

    Args:
        db: Async database session.
        user_id: Id of the user to count unread messages for.
        chat_ids: Chats to compute unread counts for.

    Returns:
        dict[UUID, int]: Unread count per chat id; chats with none are absent.
    """
    return await chats_repository.count_unread_bulk(db, user_id, chat_ids)
