"""Routes for communication between internal services."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import repository as chats_repository
from app.chats import service as chats_service
from app.dependencies import get_async_db
from app.internal.schemas import (
    BroadcastRequest,
    BroadcastResponse,
    ChatMemberIdsResponse,
    ChatMembershipResponse,
    ChatPeersResponse,
    FileAccessResponse,
    NotificationsChatResponse,
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


@router.get("/files/{file_id}/access/{user_id}")
async def check_file_access(
    file_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> FileAccessResponse:
    """Check whether a user can see some message that attaches this file.

    Used by file-orchestrator to authorize downloads/signed links. See
    app/chats/repository.py:user_can_access_file for why this is
    message-based rather than upload-chat-based.

    Args:
        file_id: Id of the file (owned by file-orchestrator).
        user_id: Id of the user requesting access.
        db: Async database session.

    Returns:
        FileAccessResponse: Whether the user is authorized.
    """
    authorized = await chats_repository.user_can_access_file(db, file_id, user_id)
    return FileAccessResponse(authorized=authorized)


@router.post("/users/{user_id}/offboard", status_code=204)
async def offboard_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Remove a deleted user's traces from this service's chat data.

    See app/chats/service.py:offboard_user. Called by administration as
    part of deleting a user's account entirely, before identity's own
    delete — so chat data is cleaned up while the account (and therefore
    this call's authorization) still makes sense to have happened.

    Args:
        user_id: Id of the user being removed.
        db: Async database session.
    """
    await chats_service.offboard_user(db, user_id)


@router.post("/users/{user_id}/notifications-chat")
async def ensure_notifications_chat(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> NotificationsChatResponse:
    """Get or create a user's personal "Уведомления" chat.

    Used by administration so an admin composing a broadcast has a real
    chat_id to upload attachments against (the admin is a member of their
    own notifications chat, like every user) before actually sending.

    Args:
        user_id: Id of the user the chat belongs to.
        db: Async database session.

    Returns:
        NotificationsChatResponse: The chat's id.
    """
    chat = await chats_service.get_or_create_notifications_chat(db, user_id)
    return NotificationsChatResponse(chat_id=chat.id)


@router.post("/broadcast")
async def broadcast(
    data: BroadcastRequest,
    db: AsyncSession = Depends(get_async_db),
) -> BroadcastResponse:
    """Send a system message into every target user's own "Уведомления" chat.

    See app/chats/service.py:broadcast_message. No permission check here —
    administration has already verified the caller is an admin/superuser.

    Args:
        data: Sender, message body, optional attachments, optional target
            user ids (None means everyone).
        db: Async database session.

    Returns:
        BroadcastResponse: How many users the message was sent to.
    """
    recipient_count = await chats_service.broadcast_message(
        db,
        sender_id=data.sender_id,
        body=data.body,
        attachment_file_ids=data.attachment_file_ids,
        target_user_ids=data.user_ids,
    )
    return BroadcastResponse(recipient_count=recipient_count)
