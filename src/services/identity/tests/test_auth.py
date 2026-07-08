"""Tests for the register and login endpoints."""

import jwt

from app.config import settings


async def test_register_success(client):
    """Register with a free username returns 201 and the new user's id."""
    resp = await client.post(
        "/auth/register",
        json={
            "username": "aboba",
            "password": "abobas123",
        },
    )
    assert resp.status_code == 201
    assert "id" in resp.json()


async def test_register_duplicate_username(client):
    """Registering an already-taken username returns 409, not 500."""
    await client.post(
        "/auth/register",
        json={
            "username": "aboba",
            "password": "abobas123",
        },
    )
    resp = await client.post(
        "/auth/register",
        json={
            "username": "aboba",
            "password": "abobas123",
        },
    )
    assert resp.status_code == 409


async def test_login_success(client):
    """Login with correct credentials returns a token pair for the registered user."""
    resp = await client.post(
        "/auth/register",
        json={
            "username": "aboba",
            "password": "abobas123",
        },
    )
    # Id of the user we just registered, to compare against the token's sub claim.
    user_id = resp.json()["id"]

    resp = await client.post(
        "/auth/login",
        json={
            "username": "aboba",
            "password": "abobas123",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body

    decoded = jwt.decode(
        body["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert decoded["sub"] == user_id


async def test_login_wrong_password(client):
    """Login with a wrong password for an existing user returns 401."""
    await client.post(
        "/auth/register",
        json={
            "username": "aboba",
            "password": "abobas123",
        },
    )
    resp = await client.post(
        "/auth/login",
        json={
            "username": "aboba",
            "password": "abibis123",
        },
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client):
    """Login for a username that was never registered returns 401."""
    resp = await client.post(
        "/auth/login",
        json={
            "username": "aboba",
            "password": "abobas123",
        },
    )
    assert resp.status_code == 401
