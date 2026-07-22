"""Business logic for chats."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import repository as chats_repository
from app.chats.models import Chat
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
