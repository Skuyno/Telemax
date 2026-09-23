"""Routes for user settings."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, get_current_user_id
from app.settings import service as settings_service
from app.settings.schemas import UserSettingsResponse, UserSettingsUpdateRequest

router = APIRouter()


@router.get("/me/settings", tags=["Settings"], response_model=UserSettingsResponse)
async def get_my_settings(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> UserSettingsResponse:
    """Get the current user's settings.

    Args:
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        UserSettingsResponse: The current user's settings, created with
        default values on first access.
    """
    settings = await settings_service.get_or_create_settings(db, user_id)
    return UserSettingsResponse.model_validate(settings)


@router.patch("/me/settings", tags=["Settings"], response_model=UserSettingsResponse)
async def update_my_settings(
    data: UserSettingsUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> UserSettingsResponse:
    """Update the current user's settings.

    Args:
        data: Fields to update; fields left unset are unchanged.
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        UserSettingsResponse: The updated settings.
    """
    settings = await settings_service.update_settings(db, user_id, data)
    return UserSettingsResponse.model_validate(settings)
