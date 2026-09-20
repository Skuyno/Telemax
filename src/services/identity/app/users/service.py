"""Business logic for users."""

from typing import Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.users import repository as users_repository
from app.users.models import User
from app.users.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from app.users.security import hash_password, verify_password

_DUMMY_HASH = hash_password("dummy-password-for-timing")


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Register a new user with a hashed password.

    Args:
        db: Async database session.
        data: Registration request body.

    Returns:
        User: The created user.
    """
    hashed_pwd = hash_password(data.password)
    return await users_repository.create_user(
        db, username=data.username, password_hash=hashed_pwd
    )


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> User | None:
    """Authenticate a user by username and password.

    Args:
        db: Async database session.
        data: Login request body.
    """
    user = await users_repository.get_user_by_username(db, data.username)
    password_hash = user.password_hash if user else _DUMMY_HASH
    if verify_password(data.password, password_hash) and user:
        return user
    return None


async def get_user_profile(db: AsyncSession, data: UUID) -> User | None:
    """Get a user's profile by id.

    Args:
        db: Async database session.
        data: User's id.

    Returns:
        User | None: The user if found, otherwise None.
    """
    user = await users_repository.get_user_by_id(db, user_id=data)
    if user:
        return user
    return None


async def update_profile(
    db: AsyncSession, user: User, data: UpdateProfileRequest
) -> User:
    """Apply a partial update to a user's own profile.

    Args:
        db: Async database session.
        user: The user to update.
        data: Fields to update; fields left unset are unchanged.

    Returns:
        User: The updated user.
    """
    patch = data.model_dump(exclude_unset=True)
    return await users_repository.update_user(db, user, patch)


async def change_password(
    db: AsyncSession, user: User, data: ChangePasswordRequest
) -> None:
    """Change a user's own password after verifying the current one.

    Bumps `token_version`, which invalidates every refresh token issued
    before the change — the closest thing to a "log out other sessions"
    this service has, and exactly what `token_version` was added for.

    Args:
        db: Async database session.
        user: The user changing their password.
        data: Current and new password.

    Raises:
        HTTPException: 401 if the current password doesn't match.
    """
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid current password")

    await users_repository.update_user(
        db,
        user,
        {
            "password_hash": hash_password(data.new_password),
            "token_version": user.token_version + 1,
        },
    )


async def get_users_bulk(db: AsyncSession, user_ids: set[UUID]) -> Sequence[User]:
    """Look up multiple users by their ids.

    Args:
        db: Async database session.
        user_ids: Set of user ids to look up.

    Returns:
        Sequence[User]: Found users; ids with no matching row are
        silently omitted from the result.
    """
    return await users_repository.get_users_bulk(db, user_ids)


async def search_users(
    db: AsyncSession,
    *,
    tag: str | None,
    email: str | None,
    phone: str | None,
    name: str | None,
    query: str | None,
    limit: int,
) -> Sequence[User]:
    """Search the user directory.

    Args:
        db: Async database session.
        tag: Tag/username prefix to search for; a leading "@" is stripped.
        email: Substring to match against email.
        phone: Substring to match against phone.
        name: Substring to match against display_name.
        query: Substring to match against email, phone, or display_name.
        limit: Maximum number of rows to return.

    Returns:
        Sequence[User]: Matching users ordered by username, capped at limit.
    """
    clean_tag = tag.lstrip("@") if tag else None
    return await users_repository.search_users(
        db,
        tag=clean_tag,
        email=email,
        phone=phone,
        name=name,
        query=query,
        limit=limit,
    )
