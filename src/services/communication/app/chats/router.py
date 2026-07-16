"""Routes for chats."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats import service as chats_service
from app.chats.schemas import CreateDirectChatRequest, CreateDirectChatResponse
from app.dependencies import get_async_db, get_current_user_id

router = APIRouter(prefix="/chats")


@router.post("/direct", status_code=201, tags=["Chats"])
async def create_direct_chat(
    data: CreateDirectChatRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> CreateDirectChatResponse:
    """Create or get an existing direct chat.

    Args:
        data: Request body with the peer's user id.
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        CreateDirectChatResponse: Id of the existing or newly created chat.
    """
    chat = await chats_service.get_or_create_direct_chat(db, user_id, data)
    return CreateDirectChatResponse.model_validate(chat)
