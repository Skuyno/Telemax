"""Tests for avatar upload, retrieval and removal."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def mock_avatar_storage():
    """Mock SeaweedFS avatar storage with an in-memory blob store."""
    blobs: dict[str, tuple[bytes, str]] = {}

    async def _put_avatar(user_id, content_type, body):
        chunks = bytearray()
        async for chunk in body:
            chunks.extend(chunk)
        blobs[user_id] = (bytes(chunks), content_type)

    async def _delete_avatar(user_id):
        blobs.pop(user_id, None)

    async def _stream_avatar(user_id):
        if user_id not in blobs:
            return None
        data, content_type = blobs[user_id]

        async def _body():
            yield data

        return _body(), content_type

    with (
        patch("app.users.service.avatar_storage.put_avatar", _put_avatar),
        patch("app.users.service.avatar_storage.delete_avatar", _delete_avatar),
        patch("app.users.router.avatar_storage.stream_avatar", _stream_avatar),
    ):
        yield blobs


async def _register_and_login(client: AsyncClient, username: str, password: str):
    body = {"username": username, "password": password}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    token = resp.json()["access_token"]

    import base64
    import json

    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    user_id = json.loads(base64.urlsafe_b64decode(padded))["sub"]
    return user_id


async def test_upload_avatar_sets_url_and_serves_bytes(client: AsyncClient):
    """Uploading an avatar sets avatar_url, and it's fetchable afterward."""
    user_id = await _register_and_login(client, "aboba", "abobas123")

    upload = await client.put(
        "/me/avatar",
        content=b"fake-jpeg-bytes",
        headers={"X-User-Id": user_id, "Content-Type": "image/jpeg"},
    )
    assert upload.status_code == 200
    avatar_url = upload.json()["avatar_url"]
    assert avatar_url.startswith(f"/users/{user_id}/avatar")

    download = await client.get(
        f"/users/{user_id}/avatar", headers={"X-User-Id": user_id}
    )
    assert download.status_code == 200
    assert download.content == b"fake-jpeg-bytes"


async def test_upload_avatar_rejects_bad_content_type(client: AsyncClient):
    """A non-image content type is rejected with 415."""
    user_id = await _register_and_login(client, "aboba", "abobas123")

    resp = await client.put(
        "/me/avatar",
        content=b"not an image",
        headers={"X-User-Id": user_id, "Content-Type": "application/pdf"},
    )
    assert resp.status_code == 415


async def test_get_avatar_missing_is_404(client: AsyncClient):
    """A user with no avatar returns 404 on fetch."""
    user_id = await _register_and_login(client, "aboba", "abobas123")

    resp = await client.get(f"/users/{user_id}/avatar", headers={"X-User-Id": user_id})
    assert resp.status_code == 404


async def test_delete_avatar_clears_url(client: AsyncClient):
    """Removing the avatar clears avatar_url and the blob stops being served."""
    user_id = await _register_and_login(client, "aboba", "abobas123")

    await client.put(
        "/me/avatar",
        content=b"fake-jpeg-bytes",
        headers={"X-User-Id": user_id, "Content-Type": "image/jpeg"},
    )

    resp = await client.delete("/me/avatar", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] is None

    resp = await client.get(f"/users/{user_id}/avatar", headers={"X-User-Id": user_id})
    assert resp.status_code == 404
