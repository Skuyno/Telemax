"""Tests for typing indicators and read receipts / unread counts."""

from uuid import uuid4

from httpx import AsyncClient


async def _create_chat(client: AsyncClient, creator_id: str, peer_id: str) -> str:
    resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": peer_id},
        headers={"X-User-Id": creator_id},
    )
    return resp.json()["id"]


async def test_typing_succeeds_for_member(client: AsyncClient):
    """A chat member can send a typing signal."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))

    resp = await client.post(
        f"/chats/{chat_id}/typing", headers={"X-User-Id": sender_id}
    )
    assert resp.status_code == 204


async def test_typing_forbidden_for_outsider(client: AsyncClient):
    """An outsider cannot send a typing signal for a chat they're not in."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    outsider = str(uuid4())

    resp = await client.post(
        f"/chats/{chat_id}/typing", headers={"X-User-Id": outsider}
    )
    assert resp.status_code == 403


async def test_unread_count_for_recipient(client: AsyncClient):
    """Messages from the peer count as unread until marked read."""
    sender_id = str(uuid4())
    reader_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, reader_id)

    await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "hi", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    msg2 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "hi again", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    last_message_id = msg2.json()["id"]

    chats = await client.get("/chats", headers={"X-User-Id": reader_id})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["unread_count"] == 2

    mark_resp = await client.post(
        f"/chats/{chat_id}/read",
        json={"last_read_message_id": last_message_id},
        headers={"X-User-Id": reader_id},
    )
    assert mark_resp.status_code == 204

    chats_after = await client.get("/chats", headers={"X-User-Id": reader_id})
    chat_after = next(c for c in chats_after.json() if c["id"] == chat_id)
    assert chat_after["unread_count"] == 0


async def test_unread_count_ignores_own_messages(client: AsyncClient):
    """A user's own sent messages never count as unread for themselves."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))

    await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "hi", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )

    chats = await client.get("/chats", headers={"X-User-Id": sender_id})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["unread_count"] == 0


async def test_marking_an_older_message_read_does_not_hide_newer_ones(
    client: AsyncClient,
):
    """Marking read up to an older message leaves later messages unread.

    Regression test: `last_read_at` must be the referenced message's own
    `created_at`, not the time of the `/read` call — otherwise every
    message sent between the referenced one and the call would be wrongly
    swept up as read too.
    """
    sender_id = str(uuid4())
    reader_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, reader_id)

    msg1 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "first", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "second", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )

    mark_resp = await client.post(
        f"/chats/{chat_id}/read",
        json={"last_read_message_id": msg1.json()["id"]},
        headers={"X-User-Id": reader_id},
    )
    assert mark_resp.status_code == 204

    chats = await client.get("/chats", headers={"X-User-Id": reader_id})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["unread_count"] == 1


async def test_marking_an_older_message_read_does_not_move_cursor_back(
    client: AsyncClient,
):
    """A stale /read call for an older message can't un-read newer ones."""
    sender_id = str(uuid4())
    reader_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, reader_id)

    msg1 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "first", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    msg2 = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "second", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )

    await client.post(
        f"/chats/{chat_id}/read",
        json={"last_read_message_id": msg2.json()["id"]},
        headers={"X-User-Id": reader_id},
    )
    stale_resp = await client.post(
        f"/chats/{chat_id}/read",
        json={"last_read_message_id": msg1.json()["id"]},
        headers={"X-User-Id": reader_id},
    )
    assert stale_resp.status_code == 204

    chats = await client.get("/chats", headers={"X-User-Id": reader_id})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["unread_count"] == 0


async def test_mark_read_forbidden_for_outsider(client: AsyncClient):
    """An outsider cannot mark a chat they're not in as read."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    msg = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "hi", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    outsider = str(uuid4())

    resp = await client.post(
        f"/chats/{chat_id}/read",
        json={"last_read_message_id": msg.json()["id"]},
        headers={"X-User-Id": outsider},
    )
    assert resp.status_code == 403
