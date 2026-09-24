"""Business logic for users."""

import logging
from collections.abc import AsyncIterator
from typing import Sequence
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.roles import SUPERUSER, USER
from app.users import repository as users_repository
from app.users import storage as avatar_storage
from app.users.models import User
from app.users.schemas import (
    ChangePasswordRequest,
    CreateAccountRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
)
from app.users.security import hash_password, verify_password

logger = logging.getLogger(__name__)

_ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_DUMMY_HASH = hash_password("dummy-password-for-timing")


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Register a new user with a hashed password.

    Always creates a plain "user" role — self-service registration can
    never produce an admin or superuser account.

    Args:
        db: Async database session.
        data: Registration request body.

    Returns:
        User: The created user.
    """
    hashed_pwd = hash_password(data.password)
    return await users_repository.create_user(
        db, username=data.username, password_hash=hashed_pwd, role=USER
    )


async def ensure_superuser_seeded(db: AsyncSession) -> None:
    """Create the superuser account on first startup, if it doesn't exist yet.

    Idempotent: does nothing once a superuser already exists. Runs once
    at service startup (see app/main.py), not on every request.

    Args:
        db: Async database session.
    """
    if await users_repository.count_by_role(db, SUPERUSER) > 0:
        return

    try:
        await users_repository.create_user(
            db,
            username=settings.superuser_username,
            password_hash=hash_password(settings.superuser_password),
            role=SUPERUSER,
        )
        logger.info(
            "Seeded superuser account '%s'", settings.superuser_username
        )
    except IntegrityError:
        # SUPERUSER_USERNAME collides with an existing non-superuser
        # account — don't silently promote someone else's account, and
        # don't crash the whole service over it either. Needs a human to
        # pick a free username (or free up this one) and restart.
        await db.rollback()
        logger.error(
            "Cannot seed superuser: username '%s' is already taken by a "
            "non-superuser account. Set a different SUPERUSER_USERNAME.",
            settings.superuser_username,
        )


async def create_account(db: AsyncSession, data: CreateAccountRequest) -> User:
    """Create an admin or user account (internal — no permission check).

    Called by the administration service, which has already verified the
    requesting user's role is allowed to create this target role — this
    layer only enforces what CreateAccountRequest.role's own pattern
    already restricts: the target can never be "superuser" via this path,
    regardless of who's asking. Unlike self-service registration, this
    can produce an admin account.

    Args:
        db: Async database session.
        data: Username, password, and the role to assign.

    Returns:
        User: The created account.

    Raises:
        HTTPException: 409 if the username is already taken.
    """
    try:
        return await users_repository.create_user(
            db,
            username=data.username,
            password_hash=hash_password(data.password),
            role=data.role,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")


async def delete_account(db: AsyncSession, caller_id: UUID, target_id: UUID) -> None:
    """Delete an admin or user account (internal — no role-permission check).

    Called by the administration service, which has already verified the
    requesting user's role is allowed to delete this target's role. Two
    invariants are still enforced here regardless, since they're
    properties of the system, not a matter of "who's allowed": the
    superuser account can never be deleted by anyone, and an account
    can't delete itself through this action.

    Args:
        db: Async database session.
        caller_id: Id of the account requesting the deletion.
        target_id: Id of the account to delete.

    Raises:
        HTTPException: 400 if the caller targets their own account, 404
            if the target doesn't exist, 403 if the target is the
            superuser.
    """
    if target_id == caller_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    target = await users_repository.get_user_by_id(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if target.role == SUPERUSER:
        raise HTTPException(status_code=403, detail="Cannot delete this account")

    await users_repository.delete_user(db, target)


async def list_accounts(db: AsyncSession, limit: int, offset: int) -> Sequence[User]:
    """List accounts for an admin-management screen.

    Args:
        db: Async database session.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip (for pagination).

    Returns:
        Sequence[User]: Accounts ordered newest first.
    """
    return await users_repository.list_users(db, limit, offset)


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


async def reset_password(
    db: AsyncSession, user: User, data: ResetPasswordRequest
) -> None:
    """Reset a user's own password from the settings page, no current password needed.

    Same "log out other sessions" effect as change_password (bumps
    token_version) — deliberately simpler flow, not a weaker one: it
    still requires the caller to already hold a valid access token.

    Args:
        db: Async database session.
        user: The user resetting their password.
        data: The new password.
    """
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
