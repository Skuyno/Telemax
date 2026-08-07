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
    if not await chats_repository.is_user_in_chat(db, chat_id, user_id):
        raise HTTPException(status_code=403, detail="not a user chat")

    members = await chats_repository.list_chat_members(db, chat_id)
    if len(members) == 0:
        raise HTTPException(status_code=404, detail="chat not found")
    return members


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
    if not await chats_repository.is_user_in_chat(db, chat_id, user_id):
        raise HTTPException(status_code=403, detail="not a user chat")

    msg = await chats_repository.create_message(
        db, chat_id, user_id, data.body, data.client_msg_id
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
    if not await chats_repository.is_user_in_chat(db, chat_id, user_id):
        raise HTTPException(status_code=403, detail="not a user chat")

    msgs = await chats_repository.get_chat_messages(db, chat_id, limit, before_msg_id)

    return msgs
