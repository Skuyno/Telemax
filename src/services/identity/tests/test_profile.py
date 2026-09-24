"""Tests for profile update and password change endpoints."""

from httpx import AsyncClient


async def _register_and_login(
    client: AsyncClient, username: str, password: str
) -> str:
    body = {"username": username, "password": password}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return resp.json()["access_token"]


async def test_update_display_name(client: AsyncClient):
    """PATCH /me sets display_name and leaves other fields unchanged."""
    token = await _register_and_login(client, "aboba", "abobas123")

    resp = await client.patch(
        "/me",
        json={"display_name": "Aboba Abobovich"},
        headers={"X-User-Id": _user_id_from_token(token)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Aboba Abobovich"
    assert body["email"] is None


async def test_update_email_conflict(client: AsyncClient):
    """PATCH /me with an email already used by another account returns 409."""
    token_a = await _register_and_login(client, "aboba", "abobas123")
    token_b = await _register_and_login(client, "abibis", "abibis123")

    resp = await client.patch(
        "/me",
        json={"email": "shared@example.com"},
        headers={"X-User-Id": _user_id_from_token(token_a)},
    )
    assert resp.status_code == 200

    resp = await client.patch(
        "/me",
        json={"email": "shared@example.com"},
        headers={"X-User-Id": _user_id_from_token(token_b)},
    )
    assert resp.status_code == 409


async def test_update_email_rejects_invalid_shape(client: AsyncClient):
    """PATCH /me rejects a value that doesn't look like an email."""
    token = await _register_and_login(client, "aboba", "abobas123")

    resp = await client.patch(
        "/me",
        json={"email": "not-an-email"},
        headers={"X-User-Id": _user_id_from_token(token)},
    )
    assert resp.status_code == 422


async def test_change_password_success_and_relogin(client: AsyncClient):
    """Changing the password lets the user log in with the new one, not the old."""
    token = await _register_and_login(client, "aboba", "abobas123")

    resp = await client.post(
        "/me/password",
        json={"current_password": "abobas123", "new_password": "newpassword1"},
        headers={"X-User-Id": _user_id_from_token(token)},
    )
    assert resp.status_code == 204

    resp = await client.post(
        "/auth/login", json={"username": "aboba", "password": "newpassword1"}
    )
    assert resp.status_code == 200

    resp = await client.post(
        "/auth/login", json={"username": "aboba", "password": "abobas123"}
    )
    assert resp.status_code == 401


async def test_change_password_wrong_current_password(client: AsyncClient):
    """Changing the password with a wrong current password returns 401."""
    token = await _register_and_login(client, "aboba", "abobas123")

    resp = await client.post(
        "/me/password",
        json={"current_password": "wrongpassword", "new_password": "newpassword1"},
        headers={"X-User-Id": _user_id_from_token(token)},
    )
    assert resp.status_code == 401


async def test_reset_password_success_and_relogin(client: AsyncClient):
    """Resetting the password (no current password) lets login with the new one."""
    token = await _register_and_login(client, "aboba", "abobas123")

    resp = await client.post(
        "/password/reset",
        json={"new_password": "newpassword1"},
        headers={"X-User-Id": _user_id_from_token(token)},
    )
    assert resp.status_code == 204

    resp = await client.post(
        "/auth/login", json={"username": "aboba", "password": "newpassword1"}
    )
    assert resp.status_code == 200

    resp = await client.post(
        "/auth/login", json={"username": "aboba", "password": "abobas123"}
    )
    assert resp.status_code == 401


async def test_reset_password_invalidates_refresh_tokens(client: AsyncClient):
    """Resetting the password bumps token_version, like a change-password does."""
    token = await _register_and_login(client, "aboba", "abobas123")
    old_login = await client.post(
        "/auth/login", json={"username": "aboba", "password": "abobas123"}
    )
    old_refresh_token = old_login.json()["refresh_token"]

    await client.post(
        "/password/reset",
        json={"new_password": "newpassword1"},
        headers={"X-User-Id": _user_id_from_token(token)},
    )

    resp = await client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert resp.status_code == 401


def _user_id_from_token(token: str) -> str:
    """Decode the access token's `sub` claim without verifying the signature.

    The `client` fixture bypasses the API gateway, so it talks to identity
    directly with an X-User-Id header instead of an Authorization header —
    this just extracts the id that header needs to carry for these tests.
    """
    import base64
    import json

    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))["sub"]
