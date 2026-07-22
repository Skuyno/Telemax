"""Routes for users."""
import logging
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_async_db, get_current_user_id
from app.users import service as users_service
from app.users.schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenRequest,
    TokenResponse,
    UserResponse,
)
from app.users.tokens import create_access_token, create_refresh_token

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/auth/register", status_code=201, tags=["Auth"], response_model=RegisterResponse
)
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


@router.post("/auth/login", tags=["Auth"], response_model=TokenResponse)
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
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


@router.post("/auth/refresh", tags=["Auth"], response_model=TokenResponse)
async def refresh(
    data: TokenRequest,
    db: AsyncSession = Depends(get_async_db)
) -> TokenResponse:
    """Refresh the access token using a valid refresh token.

    Args:
        data: TokenRequests schemas that containing a refresh_token.
        db: Async database session.

    Returns:
        TokenResponse: The generated JWT access token and old refresh-token.
    """
    try:
        decoded = jwt.decode(
            data.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if decoded["type"] != "refresh":
            raise jwt.InvalidTokenError
        user_id = UUID(decoded["sub"])
        token_version = decoded["ver"]
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await users_service.get_user_profile(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if token_version != user.token_version:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=data.refresh_token,
    )


@router.get("/me", tags=["Users"], response_model=UserResponse)
async def me(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Get the current user's profile.

    Args:
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        UserResponse: The current user's profile.

    Raises:
        HTTPException: 404 if the user no longer exists.
    """
    user = await users_service.get_user_profile(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)
