"""Tests for /admin/accounts role-permission logic."""

from uuid import uuid4

from httpx import AsyncClient


async def test_admin_can_create_user_account(client: AsyncClient, seed_account):
    """An admin can create a plain user account."""
    admin_id = seed_account("admin")

    resp = await client.post(
        "/admin/accounts",
        json={"username": "newbie", "password": "newbiepass1", "role": "user"},
        headers={"X-User-Id": admin_id},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "user"


async def test_admin_cannot_create_admin_account(client: AsyncClient, seed_account):
    """An admin cannot create another admin account."""
    admin_id = seed_account("admin")

    resp = await client.post(
        "/admin/accounts",
        json={"username": "newadmin", "password": "newadminpass1", "role": "admin"},
        headers={"X-User-Id": admin_id},
    )
    assert resp.status_code == 403


async def test_superuser_can_create_admin_account(client: AsyncClient, seed_account):
    """A superuser can create an admin account."""
    superuser_id = seed_account("superuser")

    resp = await client.post(
        "/admin/accounts",
        json={"username": "newadmin2", "password": "newadminpass1", "role": "admin"},
        headers={"X-User-Id": superuser_id},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"


async def test_create_account_rejects_duplicate_username(
    client: AsyncClient, seed_account
):
    """A taken username is refused with 409."""
    admin_id = seed_account("admin")
    seed_account("user", username="taken")

    resp = await client.post(
        "/admin/accounts",
        json={"username": "taken", "password": "somepassword1", "role": "user"},
        headers={"X-User-Id": admin_id},
    )
    assert resp.status_code == 409


async def test_plain_user_cannot_create_account(client: AsyncClient, seed_account):
    """A plain user has no access to account-management endpoints at all."""
    user_id = seed_account("user")

    resp = await client.post(
        "/admin/accounts",
        json={"username": "sneaky", "password": "sneakypass1", "role": "user"},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 403


async def test_unknown_caller_is_unauthorized(client: AsyncClient):
    """A caller id identity doesn't recognize (stale/deleted account) is 401."""
    resp = await client.post(
        "/admin/accounts",
        json={"username": "whatever", "password": "whateverpass1", "role": "user"},
        headers={"X-User-Id": str(uuid4())},
    )
    assert resp.status_code == 401


async def test_admin_can_delete_user_account(client: AsyncClient, seed_account):
    """An admin can delete a plain user account."""
    admin_id = seed_account("admin")
    target_id = seed_account("user")

    resp = await client.delete(
        f"/admin/accounts/{target_id}", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 204


async def test_admin_cannot_delete_admin_account(client: AsyncClient, seed_account):
    """An admin cannot delete another admin account."""
    admin_id = seed_account("admin")
    other_admin_id = seed_account("admin")

    resp = await client.delete(
        f"/admin/accounts/{other_admin_id}", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 403


async def test_admin_cannot_delete_superuser_account(
    client: AsyncClient, seed_account
):
    """Nobody can delete a superuser account through this endpoint."""
    admin_id = seed_account("admin")
    superuser_id = seed_account("superuser")

    resp = await client.delete(
        f"/admin/accounts/{superuser_id}", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 403


async def test_cannot_delete_own_account(client: AsyncClient, seed_account):
    """Deleting your own account through this endpoint is refused."""
    admin_id = seed_account("admin")

    resp = await client.delete(
        f"/admin/accounts/{admin_id}", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 400


async def test_delete_nonexistent_account_is_404(client: AsyncClient, seed_account):
    """Deleting an id identity doesn't recognize returns 404."""
    admin_id = seed_account("admin")

    resp = await client.delete(
        f"/admin/accounts/{uuid4()}", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 404


async def test_list_accounts_requires_admin_or_superuser(
    client: AsyncClient, seed_account
):
    """A plain user is refused; an admin can list accounts."""
    user_id = seed_account("user")
    admin_id = seed_account("admin")

    forbidden = await client.get("/admin/accounts", headers={"X-User-Id": user_id})
    assert forbidden.status_code == 403

    allowed = await client.get("/admin/accounts", headers={"X-User-Id": admin_id})
    assert allowed.status_code == 200
    assert isinstance(allowed.json(), list)


async def test_username_available_check(client: AsyncClient, seed_account):
    """Reports a free username as available, a taken one as not."""
    admin_id = seed_account("admin")
    seed_account("user", username="taken")

    free = await client.get(
        "/admin/accounts/username-available",
        params={"username": "free"},
        headers={"X-User-Id": admin_id},
    )
    assert free.status_code == 200
    assert free.json()["available"] is True

    taken = await client.get(
        "/admin/accounts/username-available",
        params={"username": "taken"},
        headers={"X-User-Id": admin_id},
    )
    assert taken.json()["available"] is False


async def test_username_available_requires_admin_or_superuser(
    client: AsyncClient, seed_account
):
    """A plain user can't probe username availability either."""
    user_id = seed_account("user")

    resp = await client.get(
        "/admin/accounts/username-available",
        params={"username": "whatever"},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 403


async def test_deleting_an_account_offboards_it_from_communication_first(
    client: AsyncClient, seed_account, communication_calls
):
    """Deleting a user cascades into communication before identity's own delete."""
    admin_id = seed_account("admin")
    target_id = seed_account("user")

    resp = await client.delete(
        f"/admin/accounts/{target_id}", headers={"X-User-Id": admin_id}
    )

    assert resp.status_code == 204
    assert communication_calls["offboarded"] == [target_id]


# --- block / unblock --------------------------------------------------------


async def test_admin_can_block_user_account(client: AsyncClient, seed_account):
    """An admin can block a plain user account."""
    admin_id = seed_account("admin")
    target_id = seed_account("user")

    resp = await client.post(
        f"/admin/accounts/{target_id}/block", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 200
    assert resp.json()["blocked"] is True


async def test_admin_cannot_block_admin_account(client: AsyncClient, seed_account):
    """An admin cannot block another admin account."""
    admin_id = seed_account("admin")
    other_admin_id = seed_account("admin")

    resp = await client.post(
        f"/admin/accounts/{other_admin_id}/block", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 403


async def test_cannot_block_own_account(client: AsyncClient, seed_account):
    """Blocking yourself through this endpoint is refused."""
    admin_id = seed_account("admin")

    resp = await client.post(
        f"/admin/accounts/{admin_id}/block", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 400


async def test_block_nonexistent_account_is_404(client: AsyncClient, seed_account):
    """Blocking an id identity doesn't recognize returns 404."""
    admin_id = seed_account("admin")

    resp = await client.post(
        f"/admin/accounts/{uuid4()}/block", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 404


async def test_plain_user_cannot_block_anyone(client: AsyncClient, seed_account):
    """A plain user has no access to the block endpoint at all."""
    user_id = seed_account("user")
    target_id = seed_account("user")

    resp = await client.post(
        f"/admin/accounts/{target_id}/block", headers={"X-User-Id": user_id}
    )
    assert resp.status_code == 403


async def test_admin_can_unblock_a_blocked_user(client: AsyncClient, seed_account):
    """Unblocking clears the flag."""
    admin_id = seed_account("admin")
    target_id = seed_account("user")
    await client.post(
        f"/admin/accounts/{target_id}/block", headers={"X-User-Id": admin_id}
    )

    resp = await client.post(
        f"/admin/accounts/{target_id}/unblock", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 200
    assert resp.json()["blocked"] is False


# --- admin password reset ---------------------------------------------------


async def test_admin_can_reset_user_password(client: AsyncClient, seed_account):
    """An admin can reset a plain user's password."""
    admin_id = seed_account("admin")
    target_id = seed_account("user")

    resp = await client.post(
        f"/admin/accounts/{target_id}/password",
        json={"new_password": "brandnewpass1"},
        headers={"X-User-Id": admin_id},
    )
    assert resp.status_code == 200


async def test_admin_cannot_reset_admin_password(client: AsyncClient, seed_account):
    """An admin cannot reset another admin's password."""
    admin_id = seed_account("admin")
    other_admin_id = seed_account("admin")

    resp = await client.post(
        f"/admin/accounts/{other_admin_id}/password",
        json={"new_password": "brandnewpass1"},
        headers={"X-User-Id": admin_id},
    )
    assert resp.status_code == 403


async def test_cannot_reset_own_password_via_admin_endpoint(
    client: AsyncClient, seed_account
):
    """Self-targeting is refused — use the self-service reset instead."""
    admin_id = seed_account("admin")

    resp = await client.post(
        f"/admin/accounts/{admin_id}/password",
        json={"new_password": "brandnewpass1"},
        headers={"X-User-Id": admin_id},
    )
    assert resp.status_code == 400


# --- broadcast ---------------------------------------------------------------


async def test_get_broadcast_chat_requires_admin_or_superuser(
    client: AsyncClient, seed_account
):
    """A plain user can't even prepare a broadcast chat."""
    user_id = seed_account("user")

    resp = await client.post(
        "/admin/broadcast/chat", headers={"X-User-Id": user_id}
    )
    assert resp.status_code == 403


async def test_get_broadcast_chat_returns_a_chat_id(client: AsyncClient, seed_account):
    """An admin gets back a chat id to upload attachments against."""
    admin_id = seed_account("admin")

    resp = await client.post(
        "/admin/broadcast/chat", headers={"X-User-Id": admin_id}
    )
    assert resp.status_code == 200
    assert "chat_id" in resp.json()


async def test_broadcast_requires_admin_or_superuser(client: AsyncClient, seed_account):
    """A plain user can't send a broadcast."""
    user_id = seed_account("user")

    resp = await client.post(
        "/admin/broadcast",
        json={"body": "sneaky broadcast"},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 403


async def test_admin_broadcast_reaches_the_communication_service(
    client: AsyncClient, seed_account, communication_calls
):
    """An admin's broadcast is forwarded with their id as sender."""
    admin_id = seed_account("admin")
    seed_account("user")
    seed_account("user")

    resp = await client.post(
        "/admin/broadcast",
        json={"body": "Плановые работы", "attachment_file_ids": [str(uuid4())]},
        headers={"X-User-Id": admin_id},
    )

    assert resp.status_code == 200
    assert resp.json()["recipient_count"] == 3  # admin + the two seeded users
    [sent] = communication_calls["broadcasts"]
    assert sent["sender_id"] == admin_id
    assert sent["body"] == "Плановые работы"
    assert len(sent["attachment_file_ids"]) == 1
