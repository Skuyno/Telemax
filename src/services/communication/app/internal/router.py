"""Routes for communication between internal services."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import service as chats_service
from app.dependencies import get_async_db
from app.internal.schemas import ChatPeersResponse

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.get("/users/{user_id}/chat-peers")
async def get_chat_peers(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> ChatPeersResponse:
    """Return users who share at least one chat with the requested user.

    Args:
        user_id: ID of the user whose chat peers should be returned.
        db: Async database session.

    Returns:
        ChatPeersResponse: Unique IDs of users sharing a chat with the user.
    """
    peer_ids = await chats_service.list_chat_peer_ids(db, user_id)
    return ChatPeersResponse(user_ids=list(peer_ids))
