"""Shared fixtures for administration tests.

No real identity service or database involved: an in-memory fake stands
in for identity's /internal/... API, so these tests exercise only
administration's own role-permission logic and request wiring.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class _FakeResponse:
    """Minimal stand-in for an httpx.Response, just enough for the service code."""

    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def identity_db():
    """In-memory {user_id_str: {"username", "role"}} fake identity backend."""
    return {}


def _account_payload(user_id: str, account: dict) -> dict:
    return {
        "id": user_id,
        "username": account["username"],
        "email": None,
        "phone": None,
        "display_name": None,
        "avatar_url": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "role": account["role"],
    }


@pytest.fixture(autouse=True)
def mock_identity(identity_db):
    """Mock outbound httpx.AsyncClient calls to identity's /internal/... API."""

    async def fake_get(url, *args, **kwargs):
        if "/internal/users/" in url:
            user_id = url.rsplit("/", 1)[-1]
            account = identity_db.get(user_id)
            if account is None:
                return _FakeResponse(404)
            return _FakeResponse(200, _account_payload(user_id, account))

        if url.endswith("/internal/accounts/username-available"):
            username = kwargs["params"]["username"]
            taken = any(a["username"] == username for a in identity_db.values())
            return _FakeResponse(200, {"available": not taken})

        if url.endswith("/internal/accounts"):
            accounts = [_account_payload(uid, a) for uid, a in identity_db.items()]
            return _FakeResponse(200, accounts)

        raise AssertionError(f"unexpected GET {url}")

    async def fake_post(url, *args, json=None, **kwargs):
        assert url.endswith("/internal/accounts")
        if any(a["username"] == json["username"] for a in identity_db.values()):
            return _FakeResponse(409)
        user_id = str(uuid4())
        identity_db[user_id] = {"username": json["username"], "role": json["role"]}
        return _FakeResponse(201, _account_payload(user_id, identity_db[user_id]))

    async def fake_delete(url, *args, params=None, **kwargs):
        target_id = url.rsplit("/", 1)[-1]
        caller_id = params["caller_id"]
        if target_id == caller_id:
            return _FakeResponse(400)
        account = identity_db.get(target_id)
        if account is None:
            return _FakeResponse(404)
        if account["role"] == "superuser":
            return _FakeResponse(403)
        del identity_db[target_id]
        return _FakeResponse(204)

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.side_effect = fake_get
    mock_client.post.side_effect = fake_post
    mock_client.delete.side_effect = fake_delete

    with patch("app.accounts.service.httpx.AsyncClient", return_value=mock_client):
        yield


@pytest.fixture
def seed_account(identity_db):
    """Insert a fake identity account directly, bypassing the API."""

    def _seed(role: str, username: str | None = None) -> str:
        user_id = str(uuid4())
        identity_db[user_id] = {
            "username": username or f"{role}-{uuid4().hex[:8]}",
            "role": role,
        }
        return user_id

    return _seed


@pytest.fixture
async def client():
    """HTTP client wired to the app (no database, nothing to truncate)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
