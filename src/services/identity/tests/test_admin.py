"""Tests for the role model: superuser seeding and the internal /internal/accounts API.

Role-permission decisions (who may create/delete which role) live in the
administration service now, not here — these internal endpoints trust
whoever calls them (only the invariants that must hold regardless of the
caller are still checked: the superuser can't be deleted, an account
can't delete itself).
"""

from uuid import uuid4

from httpx import AsyncClient

from app.config import settings
from app.roles import ADMIN, SUPERUSER, USER
from app.users import repository as users_repository
from app.users.security import hash_password
from app.users.service import ensure_superuser_seeded


async def _create_account(db_session_maker, role: str, username: str | None = None):
    """Insert an account with a given role directly, bypassing the API."""
    async with db_session_maker() as db:
        user = await users_repository.create_user(
            db,
            username=username or f"{role}-{uuid4().hex[:8]}",
            password_hash=hash_password("irrelevant-password1"),
            role=role,
        )
        return user.id


async def test_superuser_seeded_on_first_call(db_session_maker):
    """ensure_superuser_seeded creates the configured superuser account."""
    async with db_session_maker() as db:
        await ensure_superuser_seeded(db)
        assert await users_repository.count_by_role(db, SUPERUSER) == 1

        user = await users_repository.get_user_by_username(
            db, settings.superuser_username
        )
        assert user is not None
        assert user.role == SUPERUSER


async def test_superuser_seeding_is_idempotent(db_session_maker):
    """Calling ensure_superuser_seeded again doesn't create a second one."""
    async with db_session_maker() as db:
        await ensure_superuser_seeded(db)
        await ensure_superuser_seeded(db)
        assert await users_repository.count_by_role(db, SUPERUSER) == 1


async def test_superuser_seeding_skips_username_collision(db_session_maker):
    """A pre-existing non-superuser account with that username blocks seeding.

    Doesn't crash, doesn't promote the existing account — just skips.
    """
    async with db_session_maker() as db:
        await users_repository.create_user(
            db,
            username=settings.superuser_username,
            password_hash=hash_password("someone-elses-password1"),
            role=USER,
        )
        await ensure_superuser_seeded(db)
        assert await users_repository.count_by_role(db, SUPERUSER) == 0

        user = await users_repository.get_user_by_username(
            db, settings.superuser_username
        )
        assert user is not None
        assert user.role == USER


async def test_internal_create_account(client: AsyncClient):
    """Creates an account with the given role, no permission check here."""
    resp = await client.post(
        "/internal/accounts",
        json={"username": "newadmin", "password": "newadminpass1", "role": "admin"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"


async def test_internal_create_account_duplicate_username(
    client: AsyncClient, db_session_maker
):
    """A taken username is refused with 409."""
    await _create_account(db_session_maker, USER, username="taken")

    resp = await client.post(
        "/internal/accounts",
        json={"username": "taken", "password": "somepassword1", "role": "user"},
    )
    assert resp.status_code == 409


async def test_internal_delete_account(client: AsyncClient, db_session_maker):
    """Deletes an account given a distinct caller id."""
    caller_id = await _create_account(db_session_maker, ADMIN)
    target_id = await _create_account(db_session_maker, USER)

    resp = await client.delete(
        f"/internal/accounts/{target_id}", params={"caller_id": str(caller_id)}
    )
    assert resp.status_code == 204


async def test_internal_delete_account_refuses_superuser_target(
    client: AsyncClient, db_session_maker
):
    """The superuser account can never be deleted, regardless of caller."""
    caller_id = await _create_account(db_session_maker, ADMIN)
    superuser_id = await _create_account(db_session_maker, SUPERUSER)

    resp = await client.delete(
        f"/internal/accounts/{superuser_id}", params={"caller_id": str(caller_id)}
    )
    assert resp.status_code == 403


async def test_internal_delete_account_refuses_self_delete(
    client: AsyncClient, db_session_maker
):
    """An account can't delete itself through this action."""
    caller_id = await _create_account(db_session_maker, ADMIN)

    resp = await client.delete(
        f"/internal/accounts/{caller_id}", params={"caller_id": str(caller_id)}
    )
    assert resp.status_code == 400


async def test_internal_delete_account_not_found(client: AsyncClient, db_session_maker):
    """A nonexistent target returns 404."""
    caller_id = await _create_account(db_session_maker, ADMIN)

    resp = await client.delete(
        f"/internal/accounts/{uuid4()}", params={"caller_id": str(caller_id)}
    )
    assert resp.status_code == 404


async def test_internal_list_accounts(client: AsyncClient, db_session_maker):
    """Lists accounts without any role check."""
    await _create_account(db_session_maker, USER)
    await _create_account(db_session_maker, ADMIN)

    resp = await client.get("/internal/accounts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 2


async def test_internal_username_available_check(client: AsyncClient, db_session_maker):
    """Reports a free username as available, a taken one as not."""
    await _create_account(db_session_maker, USER, username="taken")

    free = await client.get(
        "/internal/accounts/username-available", params={"username": "free"}
    )
    assert free.status_code == 200
    assert free.json()["available"] is True

    taken = await client.get(
        "/internal/accounts/username-available", params={"username": "taken"}
    )
    assert taken.json()["available"] is False
