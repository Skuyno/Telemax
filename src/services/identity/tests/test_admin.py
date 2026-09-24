"""Tests for the role model: superuser seeding and admin account management."""

from uuid import uuid4

from httpx import AsyncClient

from app.config import settings
from app.roles import ADMIN, SUPERUSER, USER
from app.users import repository as users_repository
from app.users.security import hash_password
from app.users.service import ensure_superuser_seeded


async def _create_account(db_session_maker, role: str, username: str | None = None):
    """Insert an account with a given role directly, bypassing the API.

    Self-service registration can never produce an admin/superuser
    account, so tests need a way to set one up as a precondition.
    """
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


async def test_admin_can_create_user_account(client: AsyncClient, db_session_maker):
    """An admin can create a plain user account."""
    admin_id = await _create_account(db_session_maker, ADMIN)

    resp = await client.post(
        "/admin/accounts",
        json={"username": "newbie", "password": "newbiepass1", "role": "user"},
        headers={"X-User-Id": str(admin_id)},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "user"


async def test_admin_cannot_create_admin_account(client: AsyncClient, db_session_maker):
    """An admin cannot create another admin account."""
    admin_id = await _create_account(db_session_maker, ADMIN)

    resp = await client.post(
        "/admin/accounts",
        json={"username": "newadmin", "password": "newadminpass1", "role": "admin"},
        headers={"X-User-Id": str(admin_id)},
    )
    assert resp.status_code == 403


async def test_superuser_can_create_admin_account(
    client: AsyncClient, db_session_maker
):
    """A superuser can create an admin account."""
    superuser_id = await _create_account(db_session_maker, SUPERUSER)

    resp = await client.post(
        "/admin/accounts",
        json={"username": "newadmin2", "password": "newadminpass1", "role": "admin"},
        headers={"X-User-Id": str(superuser_id)},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"


async def test_plain_user_cannot_create_account(client: AsyncClient, db_session_maker):
    """A plain user has no access to account-management endpoints at all."""
    user_id = await _create_account(db_session_maker, USER)

    resp = await client.post(
        "/admin/accounts",
        json={"username": "sneaky", "password": "sneakypass1", "role": "user"},
        headers={"X-User-Id": str(user_id)},
    )
    assert resp.status_code == 403


async def test_admin_can_delete_user_account(client: AsyncClient, db_session_maker):
    """An admin can delete a plain user account."""
    admin_id = await _create_account(db_session_maker, ADMIN)
    target_id = await _create_account(db_session_maker, USER)

    resp = await client.delete(
        f"/admin/accounts/{target_id}", headers={"X-User-Id": str(admin_id)}
    )
    assert resp.status_code == 204


async def test_admin_cannot_delete_admin_account(client: AsyncClient, db_session_maker):
    """An admin cannot delete another admin account."""
    admin_id = await _create_account(db_session_maker, ADMIN)
    other_admin_id = await _create_account(db_session_maker, ADMIN)

    resp = await client.delete(
        f"/admin/accounts/{other_admin_id}", headers={"X-User-Id": str(admin_id)}
    )
    assert resp.status_code == 403


async def test_admin_cannot_delete_superuser_account(
    client: AsyncClient, db_session_maker
):
    """Nobody can delete a superuser account through this endpoint."""
    admin_id = await _create_account(db_session_maker, ADMIN)
    other_superuser_id = await _create_account(db_session_maker, SUPERUSER)

    resp = await client.delete(
        f"/admin/accounts/{other_superuser_id}", headers={"X-User-Id": str(admin_id)}
    )
    assert resp.status_code == 403


async def test_cannot_delete_own_account(client: AsyncClient, db_session_maker):
    """Deleting your own account through this endpoint is refused."""
    admin_id = await _create_account(db_session_maker, ADMIN)

    resp = await client.delete(
        f"/admin/accounts/{admin_id}", headers={"X-User-Id": str(admin_id)}
    )
    assert resp.status_code == 400


async def test_list_accounts_requires_admin_or_superuser(
    client: AsyncClient, db_session_maker
):
    """A plain user is refused; an admin can list accounts."""
    user_id = await _create_account(db_session_maker, USER)
    admin_id = await _create_account(db_session_maker, ADMIN)

    forbidden = await client.get(
        "/admin/accounts", headers={"X-User-Id": str(user_id)}
    )
    assert forbidden.status_code == 403

    allowed = await client.get(
        "/admin/accounts", headers={"X-User-Id": str(admin_id)}
    )
    assert allowed.status_code == 200
    assert isinstance(allowed.json(), list)
