"""Tests for editing, deleting, and searching messages."""

from uuid import uuid4

from httpx import AsyncClient


async def _create_chat_with_message(client: AsyncClient, sender_id: str, body: str):
    peer_id = str(uuid4())
    chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": peer_id},
        headers={"X-User-Id": sender_id},
    )
    chat_id = chat_resp.json()["id"]

    msg_resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": body, "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    return chat_id, msg_resp.json()["id"]


async def test_edit_message_success(client: AsyncClient):
    """The sender can edit their own message; edited_at gets set."""
    sender_id = str(uuid4())
    chat_id, message_id = await _create_chat_with_message(client, sender_id, "original")

    resp = await client.patch(
        f"/chats/{chat_id}/messages/{message_id}",
        json={"body": "edited text"},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["body"] == "edited text"
    assert body["edited_at"] is not None


async def test_edit_message_forbidden_for_outsider(client: AsyncClient):
    """A user outside the chat cannot edit a message in it."""
    sender_id = str(uuid4())
    chat_id, message_id = await _create_chat_with_message(client, sender_id, "original")
    outsider = str(uuid4())

    resp = await client.patch(
        f"/chats/{chat_id}/messages/{message_id}",
        json={"body": "hijacked"},
        headers={"X-User-Id": outsider},
    )
    assert resp.status_code == 403


async def test_delete_message_clears_body(client: AsyncClient):
    """Deleting a message clears its text and marks it deleted."""
    sender_id = str(uuid4())
    chat_id, message_id = await _create_chat_with_message(client, sender_id, "secret")

    resp = await client.delete(
        f"/chats/{chat_id}/messages/{message_id}", headers={"X-User-Id": sender_id}
    )
    assert resp.status_code == 204

    history = await client.get(
        f"/chats/{chat_id}/messages?limit=10", headers={"X-User-Id": sender_id}
    )
    deleted = next(m for m in history.json() if m["id"] == message_id)
    assert deleted["is_deleted"] is True
    assert deleted["body"] == ""


async def test_delete_message_forbidden_for_non_sender(client: AsyncClient):
    """Someone other than the sender cannot delete a message."""
    sender_id = str(uuid4())
    chat_id, message_id = await _create_chat_with_message(client, sender_id, "text")
    outsider = str(uuid4())

    resp = await client.delete(
        f"/chats/{chat_id}/messages/{message_id}", headers={"X-User-Id": outsider}
    )
    assert resp.status_code == 403


async def test_search_messages_finds_case_insensitive_substring(client: AsyncClient):
    """Message search matches a case-insensitive substring of the body."""
    sender_id = str(uuid4())
    chat_id, _ = await _create_chat_with_message(client, sender_id, "Hello world")
    await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "unrelated text", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )

    resp = await client.get(
        f"/chats/{chat_id}/messages/search?query=WORLD&limit=10",
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 200
    bodies = [m["body"] for m in resp.json()]
    assert bodies == ["Hello world"]


async def test_search_messages_excludes_deleted(client: AsyncClient):
    """A deleted message doesn't show up in search results."""
    sender_id = str(uuid4())
    chat_id, message_id = await _create_chat_with_message(client, sender_id, "findme")
    await client.delete(
        f"/chats/{chat_id}/messages/{message_id}", headers={"X-User-Id": sender_id}
    )

    resp = await client.get(
        f"/chats/{chat_id}/messages/search?query=findme&limit=10",
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_messages_forbidden_for_outsider(client: AsyncClient):
    """An outsider cannot search a chat's messages."""
    sender_id = str(uuid4())
    chat_id, _ = await _create_chat_with_message(client, sender_id, "hello")
    outsider = str(uuid4())

    resp = await client.get(
        f"/chats/{chat_id}/messages/search?query=hello&limit=10",
        headers={"X-User-Id": outsider},
    )
    assert resp.status_code == 403


async def test_search_messages_requires_limit(client: AsyncClient):
    """`limit` has no default and must be supplied explicitly."""
    sender_id = str(uuid4())
    chat_id, _ = await _create_chat_with_message(client, sender_id, "hello")

    resp = await client.get(
        f"/chats/{chat_id}/messages/search?query=hello",
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 422
