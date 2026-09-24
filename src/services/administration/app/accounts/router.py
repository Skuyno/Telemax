"""Routes for admin/superuser account management.

The path stays /admin/accounts (matching what identity used to serve
directly) so the frontend contract doesn't change — only the backend
behind api-gateway's "admin" segment does.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.accounts import service as accounts_service
from app.accounts.schemas import (
    AccountResponse,
    CreateAccountRequest,
    UsernameAvailableResponse,
)
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/accounts", status_code=201)
async def create_account(
    data: CreateAccountRequest,
    caller_id: UUID = Depends(get_current_user_id),
) -> AccountResponse:
    """Create an admin or user account.

    Args:
        data: Username, password, and role for the new account.
        caller_id: User id trusted from the X-User-Id header (set by API Gateway).

    Returns:
        AccountResponse: The created account.

    Raises:
        HTTPException: 403 if the caller can't create this role, 409 if
            the username is already taken.
    """
    return await accounts_service.create_account(caller_id, data)


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: UUID,
    caller_id: UUID = Depends(get_current_user_id),
) -> None:
    """Delete an admin or user account.

    Args:
        account_id: Id of the account to delete.
        caller_id: User id trusted from the X-User-Id header (set by API Gateway).

    Raises:
        HTTPException: 400 if targeting the caller's own account, 403 if
            the caller can't delete this role, 404 if not found.
    """
    await accounts_service.delete_account(caller_id, account_id)


@router.get("/accounts/username-available")
async def check_username_available(
    username: str = Query(min_length=3, max_length=32),
    caller_id: UUID = Depends(get_current_user_id),
) -> UsernameAvailableResponse:
    """Check if a username is free, for real-time validation while typing.

    Args:
        username: Username to check.
        caller_id: User id trusted from the X-User-Id header (set by API Gateway).

    Returns:
        UsernameAvailableResponse: Whether the username is free to use.
    """
    return await accounts_service.check_username_available(caller_id, username)


@router.get("/accounts")
async def list_accounts(
    limit: int = Query(default=50, gt=0, le=200),
    offset: int = Query(default=0, ge=0),
    caller_id: UUID = Depends(get_current_user_id),
) -> list[AccountResponse]:
    """List accounts for an account-management screen.

    Args:
        limit: Maximum number of rows to return (1-200).
        offset: Number of rows to skip (for pagination).
        caller_id: User id trusted from the X-User-Id header (set by API Gateway).

    Returns:
        list[AccountResponse]: Accounts ordered newest first.
    """
    return await accounts_service.list_accounts(caller_id, limit, offset)
