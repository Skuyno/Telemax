"""Auth routes for user registration."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db
from app.users import service as users_service
from app.users.schemas import RegisterRequest, RegisterResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register_user(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_async_db),
) -> RegisterResponse:
    """Register a new user.

    Args:
        data: Registration request body.
        db: Async database session.

    Returns:
        RegisterResponse: The created user's id.

    Raises:
        HTTPException: 409 if the username is already taken.
    """
    try:
        user = await users_service.register_user(db, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    return RegisterResponse.model_validate(user)
