"""Business logic for users."""

from collections.abc import AsyncIterator
from typing import Sequence
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.users import repository as users_repository
from app.users import storage as avatar_storage
from app.users.models import User
from app.users.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from app.users.security import hash_password, verify_password

_ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

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


async def upload_avatar(
    db: AsyncSession,
    user: User,
    content_type: str,
    declared_size: int | None,
    body: AsyncIterator[bytes],
) -> User:
    """Stream a new avatar image into storage, replacing any existing one.

    Args:
        db: Async database session.
        user: The user uploading their own avatar.
        content_type: MIME type of the uploaded image.
        declared_size: Client-declared Content-Length, if any.
        body: Async byte chunk iterator for the request body.

    Returns:
        User: The user with an updated `avatar_url`.

    Raises:
        HTTPException: 415 for an unsupported content type, 413 if the
            image exceeds `max_avatar_size_bytes`.
    """
    if content_type not in _ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="unsupported image type")
    if declared_size is not None and declared_size > settings.max_avatar_size_bytes:
        raise HTTPException(status_code=413, detail="avatar exceeds allowed size")

    limit = settings.max_avatar_size_bytes

    async def _bounded_body() -> AsyncIterator[bytes]:
        received = 0
        async for chunk in body:
            received += len(chunk)
            if received > limit:
                raise HTTPException(
                    status_code=413, detail="avatar exceeds allowed size"
                )
            yield chunk

    await avatar_storage.put_avatar(str(user.id), content_type, _bounded_body())

    # Cache-busting suffix: the storage key is fixed per user, so without
    # this, a browser (or CDN) that cached the previous image by URL would
    # keep showing it after a re-upload.
    avatar_url = f"/users/{user.id}/avatar?v={uuid4().hex}"
    return await users_repository.update_user(db, user, {"avatar_url": avatar_url})


async def remove_avatar(db: AsyncSession, user: User) -> User:
    """Delete a user's avatar blob and clear `avatar_url`.

    Args:
        db: Async database session.
        user: The user removing their own avatar.

    Returns:
        User: The user with `avatar_url` cleared.
    """
    await avatar_storage.delete_avatar(str(user.id))
    return await users_repository.update_user(db, user, {"avatar_url": None})


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
