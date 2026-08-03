"""Routes for inter-service communication."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db
from app.users import service as users_service
from app.users.schemas import UserResponse

router = APIRouter()


@router.get("/internal/users/{user_id}", tags=["Internal"])
async def get_user_by_id(
    user_id: UUID, db: AsyncSession = Depends(get_async_db)
) -> UserResponse:
    """Look up a single user by id.

    Intended for inter-service calls within the Docker network.

    Args:
        user_id: Id of the user to look up.
        db: Async database session.

    Returns:
        UserResponse: The user's public profile.

    Raises:
        HTTPException: 404 if the user does not exist.
    """
    user = await users_service.get_user_profile(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return UserResponse.model_validate(user)
