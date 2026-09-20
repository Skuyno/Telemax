"""Routes for communication between internal services."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import repository as chats_repository
from app.chats import service as chats_service
from app.dependencies import get_async_db
from app.internal.schemas import (
    ChatMemberIdsResponse,
    ChatMembershipResponse,
    ChatPeersResponse,
)

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


@router.get("/chats/{chat_id}/members/{user_id}")
async def check_chat_membership(
    chat_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> ChatMembershipResponse:
    """Check whether a user is a member of a chat.

    Used by file-orchestrator to authorize uploads/downloads/deletes for a
    chat's attachments without duplicating chat membership data.

    Args:
        chat_id: Id of the chat.
        user_id: Id of the user.
        db: Async database session.

    Returns:
        ChatMembershipResponse: Whether the user is a member.
    """
    is_member = await chats_repository.is_user_in_chat(db, chat_id, user_id)
    return ChatMembershipResponse(is_member=is_member)


@router.get("/chats/{chat_id}/members")
async def list_chat_member_ids(
    chat_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> ChatMemberIdsResponse:
    """List the user ids of every member of a chat.

    Used by file-orchestrator to know who to notify with upload progress
    events over WebSocket (via ws-gateway's recipient_ids-based fan-out).

    Args:
        chat_id: Id of the chat.
        db: Async database session.

    Returns:
        ChatMemberIdsResponse: All member user ids of the chat.
    """
    members = await chats_repository.list_chat_members(db, chat_id)
    return ChatMemberIdsResponse(user_ids=[m.user_id for m in members])
