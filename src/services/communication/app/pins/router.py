"""Routes for pinning messages within a chat."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import service as chats_service
from app.chats.schemas import MessageResponse
from app.dependencies import get_async_db, get_current_user_id
from app.pins import service as pins_service
from app.pins.schemas import (
    PinMessageRequest,
    PinnedMessageResponse,
    UnpinMessageRequest,
)

router = APIRouter(prefix="/chats")


@router.post(
    "/{chat_id}/messages/{message_id}/pin", status_code=204, tags=["Messages"]
)
async def pin_message(
    chat_id: UUID,
    message_id: UUID,
    data: PinMessageRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Pin a message, either just for the caller or for the whole chat.

    Args:
        chat_id: Id of the chat.
        message_id: Id of the message to pin.
        data: Whether to pin for the caller only ("me") or everyone.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.
    """
    await pins_service.pin_message(db, chat_id, message_id, user_id, data.scope)


@router.delete(
    "/{chat_id}/messages/{message_id}/pin", status_code=204, tags=["Messages"]
)
async def unpin_message(
    chat_id: UUID,
    message_id: UUID,
    data: UnpinMessageRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Unpin a message, either just for the caller or for the whole chat.

    Args:
        chat_id: Id of the chat.
        message_id: Id of the message to unpin.
        data: Whether to unpin for the caller only ("me") or everyone.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.
    """
    await pins_service.unpin_message(db, chat_id, message_id, user_id, data.scope)


@router.get("/{chat_id}/messages/pinned", tags=["Messages"])
async def list_pinned_messages(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> list[PinnedMessageResponse]:
    """List messages currently pinned for the caller in this chat.

    Args:
        chat_id: Id of the chat.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        list[PinnedMessageResponse]: Pinned messages, newest first.
    """
    pairs = await pins_service.list_pinned_messages(db, chat_id, user_id)
    attachments = await chats_service.get_attachment_ids_bulk(
        db, [message.id for message, _ in pairs]
    )

    responses = []
    for message, is_global in pairs:
        response = PinnedMessageResponse(
            **MessageResponse.model_validate(message).model_dump(),
            pin_scope="everyone" if is_global else "me",
        )
        response.attachment_file_ids = attachments.get(message.id, [])
        responses.append(response)
    return responses
