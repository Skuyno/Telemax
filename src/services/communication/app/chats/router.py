"""Routes for chats."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import service as chats_service
from app.chats.schemas import (
    ChatMembersResponse,
    ChatResponse,
    CreateDirectChatRequest,
    CreateDirectChatResponse,
    MessageResponse,
    SendMessageRequest,
)
from app.dependencies import get_async_db, get_current_user_id

router = APIRouter(prefix="/chats")


@router.post("/direct", status_code=201, tags=["Chats"])
async def create_direct_chat(
    data: CreateDirectChatRequest,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> CreateDirectChatResponse:
    """Create or get an existing direct chat.

    Args:
        data: Request body with the peer's user id.
        response: Response object used to override the status code
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        CreateDirectChatResponse: Id of the existing or newly created chat.
    """
    chat, created = await chats_service.get_or_create_direct_chat(db, user_id, data)
    if not created:
        response.status_code = 200
    return CreateDirectChatResponse.model_validate(chat)


@router.get("", tags=["Chats"])
async def list_user_chats(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> list[ChatResponse]:
    """List all chats the current user is a member of.

    Args:
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        list[ChatResponse]: The user's chats, each with a preview of the
        most recent message (null if none yet).
    """
    chats = await chats_service.list_user_chats(db, user_id)
    last_messages = await chats_service.get_last_messages(
        db, [chat.id for chat in chats]
    )

    return [
        ChatResponse(id=chat.id, last_message=last_messages.get(chat.id))
        for chat in chats
    ]


@router.get("/{chat_id}/members", tags=["Chats"])
async def list_chat_members(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> list[ChatMembersResponse]:
    """List all members of a specific chat.

    Args:
        chat_id: Id of the chat to look up.
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        list[ChatMembersResponse]: A list of chat members with their roles and join dates.
    """
    members = await chats_service.list_chat_members(db, chat_id, user_id)
    return [ChatMembersResponse.model_validate(member) for member in members]


@router.post("/{chat_id}/messages", status_code=201, tags=["Messages"])
async def send_message(
    chat_id: UUID,
    data: SendMessageRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> MessageResponse:
    """Send a new message to a chat.

    Args:
        chat_id: Id of the target chat.
        data: Message payload containing the text body and an idempotency key.
        user_id: User id trusted for X-User-Id header.
        db: Async database session.

    Returns:
        MessageResponse: The saved message, including its generated server id and
        creation timestamp
    """
    msg = await chats_service.send_message(db, chat_id, user_id, data)
    return MessageResponse.model_validate(msg)
