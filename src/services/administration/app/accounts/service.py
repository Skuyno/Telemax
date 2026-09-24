"""Business logic for account management.

Administration has no database of its own — every write and read here
goes through identity's /internal/accounts API, which trusts that the
permission checks below have already happened.
"""

from uuid import UUID

import httpx
from fastapi import HTTPException

from app.accounts.schemas import (
    AccountResponse,
    CreateAccountRequest,
    UsernameAvailableResponse,
)
from app.config import settings
from app.roles import ADMIN, MANAGEABLE_ROLES, SUPERUSER


async def _fetch_role(user_id: UUID) -> str | None:
    """Look up a user's role via identity's internal API.

    Returns:
        str | None: The role, or None if the user doesn't exist.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.identity_url}/internal/users/{user_id}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()["role"]


async def _require_caller_role(caller_id: UUID) -> str:
    """Look up the caller's role and confirm they may use account management.

    Raises:
        HTTPException: 401 if the caller doesn't exist (a stale token for
            a deleted account), 403 if their role is plain "user".
    """
    role = await _fetch_role(caller_id)
    if role is None:
        raise HTTPException(status_code=401, detail="User not found")
    if role not in (ADMIN, SUPERUSER):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return role


async def create_account(
    caller_id: UUID, data: CreateAccountRequest
) -> AccountResponse:
    """Create an admin or user account.

    A superuser can create admin or user accounts; an admin can only
    create user accounts.

    Raises:
        HTTPException: 403 if the caller's role can't create this role,
            409 if the username is already taken.
    """
    caller_role = await _require_caller_role(caller_id)

    if data.role not in MANAGEABLE_ROLES.get(caller_role, set()):
        raise HTTPException(status_code=403, detail="Cannot create this role")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.identity_url}/internal/accounts", json=data.model_dump()
        )
    if response.status_code == 409:
        raise HTTPException(status_code=409, detail="Username already taken")
    response.raise_for_status()
    return AccountResponse.model_validate(response.json())


async def delete_account(caller_id: UUID, target_id: UUID) -> None:
    """Delete an admin or user account.

    A superuser can delete admin or user accounts; an admin can only
    delete user accounts. Deleting your own account, and deleting the
    superuser account, are refused by identity itself regardless of what
    happens here — those are invariants of the system, not a matter of
    role permissions.

    Raises:
        HTTPException: 400 if targeting the caller's own account, 404 if
            the target doesn't exist, 403 if the caller's role can't
            delete the target's role.
    """
    caller_role = await _require_caller_role(caller_id)

    if target_id == caller_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    target_role = await _fetch_role(target_id)
    if target_role is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if target_role not in MANAGEABLE_ROLES.get(caller_role, set()):
        raise HTTPException(status_code=403, detail="Cannot delete this account")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.identity_url}/internal/accounts/{target_id}",
            params={"caller_id": str(caller_id)},
        )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Account not found")
    response.raise_for_status()


async def list_accounts(
    caller_id: UUID, limit: int, offset: int
) -> list[AccountResponse]:
    """List accounts for an account-management screen.

    Raises:
        HTTPException: 403 if the caller isn't admin/superuser.
    """
    await _require_caller_role(caller_id)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.identity_url}/internal/accounts",
            params={"limit": limit, "offset": offset},
        )
    response.raise_for_status()
    return [AccountResponse.model_validate(a) for a in response.json()]


async def check_username_available(
    caller_id: UUID, username: str
) -> UsernameAvailableResponse:
    """Check if a username is free, for real-time validation while typing.

    Raises:
        HTTPException: 403 if the caller isn't admin/superuser.
    """
    await _require_caller_role(caller_id)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.identity_url}/internal/accounts/username-available",
            params={"username": username},
        )
    response.raise_for_status()
    return UsernameAvailableResponse.model_validate(response.json())
