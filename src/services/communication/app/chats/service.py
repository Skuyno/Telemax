"""Business logic for chats."""

from typing import Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import repository as chats_repository
from app.chats.models import Chat, Message
from app.chats.schemas import CreateDirectChatRequest


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
