"""Routes for per-chat settings."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, get_current_user_id
from app.settings import service as settings_service
from app.settings.schemas import ChatSettingsResponse, ChatSettingsUpdateRequest

router = APIRouter(prefix="/chats")


@router.get(
    "/{chat_id}/settings", tags=["Settings"], response_model=ChatSettingsResponse
)
async def get_chat_settings(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> ChatSettingsResponse:
    """Get the current user's settings for a chat.

    Args:
        chat_id: Id of the chat.
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        ChatSettingsResponse: The user's settings for the chat, created with
        default values on first access.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    settings = await settings_service.get_or_create_settings(db, chat_id, user_id)
    return ChatSettingsResponse.model_validate(settings)


@router.patch(
    "/{chat_id}/settings", tags=["Settings"], response_model=ChatSettingsResponse
)
async def update_chat_settings(
    chat_id: UUID,
    data: ChatSettingsUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> ChatSettingsResponse:
    """Update the current user's settings for a chat.

    Args:
        chat_id: Id of the chat.
        data: Fields to update; fields left unset are unchanged.
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        ChatSettingsResponse: The updated settings.

    Raises:
        HTTPException: 403 if the user is not a member of the chat.
    """
    settings = await settings_service.update_settings(db, chat_id, user_id, data)
    return ChatSettingsResponse.model_validate(settings)
