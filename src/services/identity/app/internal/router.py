"""Routes for inter-service communication.

No auth of their own — these trust the caller (another service on the
internal Docker network), not a user. In particular, the /accounts
endpoints do no role-permission checks: the administration service is
expected to have already decided the requesting user's role allows the
action, before ever calling here.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db
from app.users import repository as users_repository
from app.users import service as users_service
from app.users.schemas import (
    CreateAccountRequest,
    UsernameAvailableResponse,
    UserResponse,
)

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.get("/users/{user_id}")
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


@router.post("/accounts", status_code=201)
async def create_account(
    data: CreateAccountRequest, db: AsyncSession = Depends(get_async_db)
) -> UserResponse:
    """Create an admin or user account. See app/users/service.py:create_account.

    Args:
        data: Username, password, and the role to assign.
        db: Async database session.

    Returns:
        UserResponse: The created account.

    Raises:
        HTTPException: 409 if the username is already taken.
    """
    account = await users_service.create_account(db, data)
    return UserResponse.model_validate(account)


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: UUID,
    caller_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Delete an admin or user account. See app/users/service.py:delete_account.

    Args:
        account_id: Id of the account to delete.
        caller_id: Id of the account requesting the deletion (still
            checked here for the self-delete and superuser invariants).
        db: Async database session.

    Raises:
        HTTPException: 400 if targeting the caller's own account, 404 if
            not found, 403 if the target is the superuser.
    """
    await users_service.delete_account(db, caller_id, account_id)


@router.get("/accounts")
async def list_accounts(
    limit: int = Query(default=50, gt=0, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
) -> list[UserResponse]:
    """List accounts, newest first. See app/users/service.py:list_accounts.

    Args:
        limit: Maximum number of rows to return (1-200).
        offset: Number of rows to skip (for pagination).
        db: Async database session.

    Returns:
        list[UserResponse]: Accounts ordered newest first.
    """
    accounts = await users_service.list_accounts(db, limit, offset)
    return [UserResponse.model_validate(a) for a in accounts]


@router.get("/accounts/username-available")
async def check_username_available(
    username: str = Query(min_length=3, max_length=32),
    db: AsyncSession = Depends(get_async_db),
) -> UsernameAvailableResponse:
    """Check if a username is free, for real-time validation while typing.

    Args:
        username: Username to check.
        db: Async database session.

    Returns:
        UsernameAvailableResponse: Whether the username is free to use.
    """
    existing = await users_repository.get_user_by_username(db, username)
    return UsernameAvailableResponse(available=existing is None)
