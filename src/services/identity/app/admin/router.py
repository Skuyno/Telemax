"""Routes for admin/superuser account management.

Every route here requires the caller to already be an admin or superuser
(enforced by `require_role`) — this is not part of the public API surface
a plain user ever touches.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, require_role
from app.roles import ADMIN, SUPERUSER
from app.users import service as users_service
from app.users.models import User
from app.users.schemas import CreateAccountRequest, UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/accounts", status_code=201)
async def create_account(
    data: CreateAccountRequest,
    caller: User = Depends(require_role(SUPERUSER, ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Create an admin or user account.

    A superuser can create admin or user accounts; an admin can only
    create user accounts.

    Args:
        data: Username, password, and role for the new account.
        caller: The authenticated caller (must be admin or superuser).
        db: Async database session.

    Returns:
        UserResponse: The created account.

    Raises:
        HTTPException: 403 if the caller can't create this role, 409 if
            the username is already taken.
    """
    account = await users_service.create_account(db, caller, data)
    return UserResponse.model_validate(account)


@router.delete("/accounts/{user_id}", status_code=204)
async def delete_account(
    user_id: UUID,
    caller: User = Depends(require_role(SUPERUSER, ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Delete an admin or user account.

    A superuser can delete admin or user accounts; an admin can only
    delete user accounts. The superuser account itself can never be
    deleted through this endpoint, by anyone.

    Args:
        user_id: Id of the account to delete.
        caller: The authenticated caller (must be admin or superuser).
        db: Async database session.

    Raises:
        HTTPException: 400 if targeting the caller's own account, 403 if
            the caller can't delete this role, 404 if not found.
    """
    await users_service.delete_account(db, caller, user_id)


@router.get("/accounts")
async def list_accounts(
    limit: int = Query(default=50, gt=0, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_role(SUPERUSER, ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> list[UserResponse]:
    """List accounts for an account-management screen.

    Args:
        limit: Maximum number of rows to return (1-200).
        offset: Number of rows to skip (for pagination).
        _: The authenticated caller (must be admin or superuser).
        db: Async database session.

    Returns:
        list[UserResponse]: Accounts ordered newest first.
    """
    accounts = await users_service.list_accounts(db, limit, offset)
    return [UserResponse.model_validate(a) for a in accounts]
