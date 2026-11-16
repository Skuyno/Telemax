"""Tests for replying to a message within the same chat."""

from uuid import uuid4

from httpx import AsyncClient


async def _create_chat(client: AsyncClient, creator_id: str, peer_id: str) -> str:
    resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": peer_id},
        headers={"X-User-Id": creator_id},
    )
    return resp.json()["id"]


async def test_reply_to_message_sets_reply_to_message_id(client: AsyncClient):
    """A reply carries the id of the message it replies to."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))

    original = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "original", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    original_id = original.json()["id"]

    reply = await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "a reply",
            "client_msg_id": str(uuid4()),
            "reply_to_message_id": original_id,
        },
        headers={"X-User-Id": sender_id},
    )
    assert reply.status_code == 201
    assert reply.json()["reply_to_message_id"] == original_id


async def test_reply_to_nonexistent_message_returns_404(client: AsyncClient):
    """Replying to a message id that doesn't exist in the chat fails with 404."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))

    resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "a reply",
            "client_msg_id": str(uuid4()),
            "reply_to_message_id": str(uuid4()),
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 404


async def test_reply_to_a_message_from_another_chat_returns_404(client: AsyncClient):
    """A reply target must belong to the same chat the reply is sent in."""
    sender_id = str(uuid4())
    other_chat_id = await _create_chat(client, sender_id, str(uuid4()))
    other_msg = await client.post(
        f"/chats/{other_chat_id}/messages",
        json={"body": "elsewhere", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    other_message_id = other_msg.json()["id"]

    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "a reply",
            "client_msg_id": str(uuid4()),
            "reply_to_message_id": other_message_id,
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 404


async def test_reply_to_a_deleted_message_returns_404(client: AsyncClient):
    """A deleted message can no longer be replied to."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))

    original = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "gone soon", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    original_id = original.json()["id"]
    await client.delete(
        f"/chats/{chat_id}/messages/{original_id}", headers={"X-User-Id": sender_id}
    )

    resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "a reply",
            "client_msg_id": str(uuid4()),
            "reply_to_message_id": original_id,
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 404


async def test_message_without_reply_has_null_reply_to_message_id(client: AsyncClient):
    """A plain message has no reply_to_message_id."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))

    resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "plain", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    assert resp.json()["reply_to_message_id"] is None
