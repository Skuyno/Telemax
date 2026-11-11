"""Tests for deleting several of the caller's own messages at once."""

from uuid import uuid4

from httpx import AsyncClient


async def _create_chat(client: AsyncClient, creator_id: str, peer_id: str) -> str:
    resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": peer_id},
        headers={"X-User-Id": creator_id},
    )
    return resp.json()["id"]


async def _send(client: AsyncClient, chat_id: str, sender_id: str, body: str) -> str:
    resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": body, "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    return resp.json()["id"]


async def _history(client: AsyncClient, chat_id: str, user_id: str) -> list[dict]:
    resp = await client.get(
        f"/chats/{chat_id}/messages?limit=20", headers={"X-User-Id": user_id}
    )
    return resp.json()


async def test_bulk_delete_removes_all_listed_messages(client: AsyncClient):
    """Deleting a batch soft-deletes every message in it."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    ids = [await _send(client, chat_id, sender_id, f"msg {i}") for i in range(3)]

    resp = await client.post(
        f"/chats/{chat_id}/messages/delete",
        json={"message_ids": ids},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 204

    history = await _history(client, chat_id, sender_id)
    deleted_by_id = {m["id"]: m for m in history}
    for message_id in ids:
        assert deleted_by_id[message_id]["is_deleted"] is True
        assert deleted_by_id[message_id]["body"] == ""


async def test_bulk_delete_is_all_or_nothing_for_someone_elses_message(
    client: AsyncClient,
):
    """One message not owned by the caller means nothing is deleted."""
    sender_id = str(uuid4())
    chat_id, peer_id = None, str(uuid4())
    chat_id = await _create_chat(client, sender_id, peer_id)
    own_id = await _send(client, chat_id, sender_id, "mine")
    others_id = await _send(client, chat_id, peer_id, "not mine")

    resp = await client.post(
        f"/chats/{chat_id}/messages/delete",
        json={"message_ids": [own_id, others_id]},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 403

    history = await _history(client, chat_id, sender_id)
    by_id = {m["id"]: m for m in history}
    assert by_id[own_id]["is_deleted"] is False
    assert by_id[others_id]["is_deleted"] is False


async def test_bulk_delete_is_all_or_nothing_for_a_message_from_another_chat(
    client: AsyncClient,
):
    """A message id from a different chat invalidates the whole batch."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    other_chat_id = await _create_chat(client, sender_id, str(uuid4()))
    own_id = await _send(client, chat_id, sender_id, "mine")
    other_chat_msg_id = await _send(client, other_chat_id, sender_id, "elsewhere")

    resp = await client.post(
        f"/chats/{chat_id}/messages/delete",
        json={"message_ids": [own_id, other_chat_msg_id]},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 404

    history = await _history(client, chat_id, sender_id)
    assert next(m for m in history if m["id"] == own_id)["is_deleted"] is False


async def test_bulk_delete_forbidden_for_outsider(client: AsyncClient):
    """A non-member can't bulk-delete in a chat they don't belong to."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    message_id = await _send(client, chat_id, sender_id, "hi")
    outsider = str(uuid4())

    resp = await client.post(
        f"/chats/{chat_id}/messages/delete",
        json={"message_ids": [message_id]},
        headers={"X-User-Id": outsider},
    )
    assert resp.status_code == 403


async def test_bulk_delete_rejects_empty_list(client: AsyncClient):
    """An empty message_ids list is a validation error, not a no-op success."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))

    resp = await client.post(
        f"/chats/{chat_id}/messages/delete",
        json={"message_ids": []},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 422
