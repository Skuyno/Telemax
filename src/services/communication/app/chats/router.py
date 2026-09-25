"""Routes for chats."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import service as chats_service
from app.chats.models import Message
from app.chats.schemas import (
    ChatMembersResponse,
    ChatResponse,
    CreateDirectChatRequest,
    CreateDirectChatResponse,
    CreateGroupChatRequest,
    CreateGroupChatResponse,
    EditMessageRequest,
    MarkChatReadRequest,
    MessageResponse,
    SendMessageRequest,
)
from app.dependencies import get_async_db, get_current_user_id

router = APIRouter(prefix="/chats")


def _to_message_response(msg: Message, attachment_ids: list[UUID]) -> MessageResponse:
    """Build a MessageResponse from an ORM row plus its attachment ids.

    Message doesn't carry attachments as an ORM relationship (this codebase
    keeps cross-concern data as plain lookups, not relationships), so the
    ids are always merged in explicitly at this boundary.
    """
    response = MessageResponse.model_validate(msg)
    response.attachment_file_ids = attachment_ids
    return response


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
    chat_ids = [chat.id for chat in chats]
    last_messages = await chats_service.get_last_messages(db, chat_ids)
    unread_counts = await chats_service.get_unread_counts(db, user_id, chat_ids)

    return [
        ChatResponse(
            id=chat.id,
            last_message=last_messages.get(chat.id),
            unread_count=unread_counts.get(chat.id, 0),
        )
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
        list[ChatMembersResponse]: A list of chat members
            with their roles and join dates.
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
    attachment_ids = await chats_service.get_attachment_ids(db, msg.id)
    return _to_message_response(msg, attachment_ids)


@router.get("/{chat_id}/messages", tags=["Messages"])
async def get_chat_messages(
    chat_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    before_msg_id: UUID | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> list[MessageResponse]:
    """Get paginated message history for a chat.

    Args:
        chat_id: Id of the target chat.
        limit: Maximum number of messages to return (1-100).
        before_msg_id: Optional message ID cursor to load older messages.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        list[MessageResponse]: A list of messages ordered from newest to oldest.
    """
    msgs = await chats_service.get_chat_messages(
        db, chat_id, user_id, limit, before_msg_id
    )
    attachments_by_message = await chats_service.get_attachment_ids_bulk(
        db, [msg.id for msg in msgs]
    )

    return [
        _to_message_response(msg, attachments_by_message.get(msg.id, []))
        for msg in msgs
    ]


@router.get("/{chat_id}/messages/search", tags=["Messages"])
async def search_messages(
    chat_id: UUID,
    query: str = Query(min_length=1),
    limit: int = Query(gt=0),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> list[MessageResponse]:
    """Search a chat's messages by a case-insensitive substring.

    Args:
        chat_id: Id of the chat to search within.
        query: Substring to match against message text.
        limit: Maximum number of results to return (required, no default).
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        list[MessageResponse]: Matching messages, newest first.
    """
    msgs = await chats_service.search_messages(db, chat_id, user_id, query, limit)
    attachments_by_message = await chats_service.get_attachment_ids_bulk(
        db, [msg.id for msg in msgs]
    )

    return [
        _to_message_response(msg, attachments_by_message.get(msg.id, []))
        for msg in msgs
    ]


@router.patch("/{chat_id}/messages/{message_id}", tags=["Messages"])
async def edit_message(
    chat_id: UUID,
    message_id: UUID,
    data: EditMessageRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> MessageResponse:
    """Edit a message's text. Only the original sender may edit it.

    Args:
        chat_id: Id of the chat the message belongs to.
        message_id: Id of the message to edit.
        data: New text content.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        MessageResponse: The updated message.
    """
    msg = await chats_service.edit_message(db, chat_id, message_id, user_id, data.body)
    attachment_ids = await chats_service.get_attachment_ids(db, msg.id)
    return _to_message_response(msg, attachment_ids)


@router.delete("/{chat_id}/messages/{message_id}", status_code=204, tags=["Messages"])
async def delete_message(
    chat_id: UUID,
    message_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Delete a message (soft delete). Only the original sender may delete it.

    Args:
        chat_id: Id of the chat the message belongs to.
        message_id: Id of the message to delete.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.
    """
    await chats_service.delete_message(db, chat_id, message_id, user_id)


@router.post("/{chat_id}/typing", status_code=204, tags=["Chats"])
async def send_typing(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Notify other chat members that the current user is typing.

    Args:
        chat_id: Id of the chat.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.
    """
    await chats_service.send_typing(db, chat_id, user_id)


@router.post("/{chat_id}/read", status_code=204, tags=["Chats"])
async def mark_chat_read(
    chat_id: UUID,
    data: MarkChatReadRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Mark a chat read up to (and including) a given message.

    Args:
        chat_id: Id of the chat.
        data: Id of the last message read.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.
    """
    await chats_service.mark_chat_read(db, chat_id, user_id, data.last_read_message_id)


@router.post("/group", status_code=201, tags=["Chats"])
async def create_group_chat(
    data: CreateGroupChatRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> CreateGroupChatResponse:
    """Create a new group chat.

    Args:
        data: Group title and initial member ids.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        CreateGroupChatResponse: Id of the newly created group chat.
    """
    chat = await chats_service.create_group_chat(db, user_id, data)
    return CreateGroupChatResponse.model_validate(chat)
