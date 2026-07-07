"""Auth routes for user registration."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db
from app.users import service as users_service
from app.users.schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.users.tokens import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(
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


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Authenticate a user and return a pair of JWT tokens.

    Args:
        data: Login request body.
        db: Async database session.

    Returns:
        TokenResponse: The generated JWT tokens.

    Raises:
        HTTPException: 401 if the credentials are invalid.
    """
    user = await users_service.authenticate_user(db, data)
    if user is None:
        logger.warning("login failed for username: %s", data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
