"""Routes for users."""

import logging
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_async_db, get_current_user_id
from app.users import service as users_service
from app.users.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
    UserSearchRequest,
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
    data: TokenRequest, db: AsyncSession = Depends(get_async_db)
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


@router.patch("/me", tags=["Users"], response_model=UserResponse)
async def update_me(
    data: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Update the current user's profile (display name and/or email).

    Args:
        data: Fields to update; fields left unset are unchanged.
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Returns:
        UserResponse: The updated profile.

    Raises:
        HTTPException: 404 if the user no longer exists, 409 if the email
            is already used by another account.
    """
    user = await users_service.get_user_profile(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user = await users_service.update_profile(db, user, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already in use")
    return UserResponse.model_validate(user)


@router.post("/me/password", status_code=204, tags=["Users"])
async def change_my_password(
    data: ChangePasswordRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Change the current user's own password.

    Requires the current password. Invalidates existing refresh tokens
    (bumps `token_version`) — other sessions will need to log in again.

    Args:
        data: Current and new password.
        user_id: User id trusted from the X-User-Id header (set by API Gateway).
        db: Async database session.

    Raises:
        HTTPException: 404 if the user no longer exists, 401 if the
            current password doesn't match.
    """
    user = await users_service.get_user_profile(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await users_service.change_password(db, user, data)


@router.get("/users", tags=["Users"])
async def get_users_bulk(
    ids: list[UUID] = Query(...), db: AsyncSession = Depends(get_async_db)
) -> list[UserResponse]:
    """Return public profiles for a batch of known user ids.

    Used by authenticated clients to resolve user ids received from chat
    endpoints into profiles suitable for display.

    Args:
        ids: User ids passed as repeated query parameters.
        db: Async database session.

    Returns:
        list[UserResponse]: Profiles of found users; missing ids are
        silently omitted.
    """
    users = await users_service.get_users_bulk(db, ids)
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users/search", tags=["Users"], response_model=list[UserResponse])
async def search_users(
    data: UserSearchRequest,
    db: AsyncSession = Depends(get_async_db),
) -> list[UserResponse]:
    """Search the user directory by tag, email, phone, and/or name.

    `tag` matches only a prefix of the username (an optional leading "@"
    is ignored); `email`, `phone`, and `name` match any substring; `query`
    is a shortcut that matches a substring against email, phone, or name
    all at once (never against tag). Matching is case-insensitive. There
    is no built-in page size: pass a larger `limit` on each subsequent
    request (e.g. 30, then 60, then 90) to page through more results.

    Args:
        data: Search filters and the result limit.
        db: Async database session.

    Returns:
        list[UserResponse]: Up to `limit` matching profiles ordered by
        username.
    """
    users = await users_service.search_users(
        db,
        tag=data.tag,
        email=data.email,
        phone=data.phone,
        name=data.name,
        query=data.query,
        limit=data.limit,
    )
    return [UserResponse.model_validate(u) for u in users]
