"""Tests for group chat avatar upload, retrieval and removal."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def mock_avatar_storage():
    """Mock SeaweedFS chat-avatar storage with an in-memory blob store."""
    blobs: dict[str, tuple[bytes, str]] = {}

    async def _put_avatar(chat_id, content_type, body):
        chunks = bytearray()
        async for chunk in body:
            chunks.extend(chunk)
        blobs[chat_id] = (bytes(chunks), content_type)

    async def _delete_avatar(chat_id):
        blobs.pop(chat_id, None)

    async def _stream_avatar(chat_id):
        if chat_id not in blobs:
            return None
        data, content_type = blobs[chat_id]

        async def _body():
            yield data

        return _body(), content_type

    with (
        patch("app.chats.service.chats_storage.put_avatar", _put_avatar),
        patch("app.chats.service.chats_storage.delete_avatar", _delete_avatar),
        patch("app.chats.router.chats_storage.stream_avatar", _stream_avatar),
    ):
        yield blobs


async def _create_group(client: AsyncClient, owner: str, member: str) -> str:
    resp = await client.post(
        "/chats/group",
        json={"title": "Team", "member_ids": [member]},
        headers={"X-User-Id": owner},
    )
    return resp.json()["id"]


async def test_owner_can_upload_avatar(client: AsyncClient, mock_nats_client):
    """The group owner can set an avatar, served back and visible in the list."""
    owner = str(uuid4())
    member = str(uuid4())
    chat_id = await _create_group(client, owner, member)

    upload = await client.put(
        f"/chats/{chat_id}/avatar",
        content=b"fake-png-bytes",
        headers={"X-User-Id": owner, "Content-Type": "image/png"},
    )
    assert upload.status_code == 204

    download = await client.get(
        f"/chats/{chat_id}/avatar", headers={"X-User-Id": owner}
    )
    assert download.status_code == 200
    assert download.content == b"fake-png-bytes"

    chats = await client.get("/chats", headers={"X-User-Id": owner})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["avatar_url"] is not None


async def test_non_owner_cannot_upload_avatar(client: AsyncClient):
    """A plain member can't set the group's avatar."""
    owner = str(uuid4())
    member = str(uuid4())
    chat_id = await _create_group(client, owner, member)

    resp = await client.put(
        f"/chats/{chat_id}/avatar",
        content=b"fake-png-bytes",
        headers={"X-User-Id": member, "Content-Type": "image/png"},
    )
    assert resp.status_code == 403


async def test_upload_rejects_bad_content_type(client: AsyncClient):
    """A non-image content type is rejected with 415."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner, str(uuid4()))

    resp = await client.put(
        f"/chats/{chat_id}/avatar",
        content=b"not an image",
        headers={"X-User-Id": owner, "Content-Type": "application/pdf"},
    )
    assert resp.status_code == 415


async def test_get_avatar_missing_is_404(client: AsyncClient):
    """A group with no avatar returns 404 on fetch."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner, str(uuid4()))

    resp = await client.get(f"/chats/{chat_id}/avatar", headers={"X-User-Id": owner})
    assert resp.status_code == 404


async def test_avatar_forbidden_for_outsider(client: AsyncClient):
    """Someone outside the chat can't view its avatar."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner, str(uuid4()))
    outsider = str(uuid4())

    await client.put(
        f"/chats/{chat_id}/avatar",
        content=b"fake-png-bytes",
        headers={"X-User-Id": owner, "Content-Type": "image/png"},
    )
    resp = await client.get(
        f"/chats/{chat_id}/avatar", headers={"X-User-Id": outsider}
    )
    assert resp.status_code == 403


async def test_owner_can_remove_avatar(client: AsyncClient, mock_nats_client):
    """Removing the avatar clears it from the chat list and 404s on fetch."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner, str(uuid4()))

    await client.put(
        f"/chats/{chat_id}/avatar",
        content=b"fake-png-bytes",
        headers={"X-User-Id": owner, "Content-Type": "image/png"},
    )
    resp = await client.delete(
        f"/chats/{chat_id}/avatar", headers={"X-User-Id": owner}
    )
    assert resp.status_code == 204

    chats = await client.get("/chats", headers={"X-User-Id": owner})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["avatar_url"] is None

    download = await client.get(
        f"/chats/{chat_id}/avatar", headers={"X-User-Id": owner}
    )
    assert download.status_code == 404


async def test_non_owner_cannot_remove_avatar(client: AsyncClient):
    """A plain member can't remove the group's avatar."""
    owner = str(uuid4())
    member = str(uuid4())
    chat_id = await _create_group(client, owner, member)

    resp = await client.delete(
        f"/chats/{chat_id}/avatar", headers={"X-User-Id": member}
    )
    assert resp.status_code == 403


async def test_direct_chat_has_no_avatar_endpoint_access(client: AsyncClient):
    """A direct chat isn't a group — avatar upload is rejected with 409."""
    user_a = str(uuid4())
    user_b = str(uuid4())
    chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": user_b},
        headers={"X-User-Id": user_a},
    )
    chat_id = chat_resp.json()["id"]

    resp = await client.put(
        f"/chats/{chat_id}/avatar",
        content=b"fake-png-bytes",
        headers={"X-User-Id": user_a, "Content-Type": "image/png"},
    )
    assert resp.status_code == 409
