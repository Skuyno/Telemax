"""Tests for the service message created when a message is pinned for everyone."""

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
    return chat_id, msg_resp.json()["id"], peer_id


async def _history(client: AsyncClient, chat_id: str, user_id: str) -> list[dict]:
    resp = await client.get(
        f"/chats/{chat_id}/messages?limit=20", headers={"X-User-Id": user_id}
    )
    assert resp.status_code == 200
    return resp.json()


async def test_pinning_for_everyone_adds_a_service_message(client: AsyncClient):
    """Pinning "for everyone" writes a visible service message into history."""
    sender_id = str(uuid4())
    chat_id, message_id, peer_id = await _create_chat_with_message(
        client, sender_id, "important"
    )

    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )

    history = await _history(client, chat_id, peer_id)
    service_messages = [m for m in history if m["kind"] == "service"]
    assert len(service_messages) == 1
    service_message = service_messages[0]
    assert service_message["service_action"] == "message_pinned"
    assert service_message["service_target_message_id"] == message_id
    assert service_message["sender_id"] == sender_id


async def test_pinning_for_me_does_not_add_a_service_message(client: AsyncClient):
    """A personal pin is invisible to others — no service message either."""
    sender_id = str(uuid4())
    chat_id, message_id, peer_id = await _create_chat_with_message(
        client, sender_id, "just for me"
    )

    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "me"},
        headers={"X-User-Id": sender_id},
    )

    history = await _history(client, chat_id, peer_id)
    assert all(m["kind"] != "service" for m in history)


async def test_unpinning_does_not_add_a_service_message(client: AsyncClient):
    """Unpinning stays silent, matching Telegram's behavior."""
    sender_id = str(uuid4())
    chat_id, message_id, peer_id = await _create_chat_with_message(
        client, sender_id, "important"
    )
    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    await client.request(
        "DELETE",
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )

    history = await _history(client, chat_id, peer_id)
    assert len([m for m in history if m["kind"] == "service"]) == 1


async def test_pinning_again_after_unpin_adds_another_service_message(
    client: AsyncClient,
):
    """Re-pinning the same message is a new, distinct event with its own entry."""
    sender_id = str(uuid4())
    chat_id, message_id, _ = await _create_chat_with_message(
        client, sender_id, "important"
    )

    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    await client.request(
        "DELETE",
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )

    history = await _history(client, chat_id, sender_id)
    assert len([m for m in history if m["kind"] == "service"]) == 2


async def test_last_message_preview_reflects_a_service_message(client: AsyncClient):
    """GET /chats' last_message preview carries the same kind/service fields."""
    sender_id = str(uuid4())
    chat_id, message_id, _ = await _create_chat_with_message(
        client, sender_id, "important"
    )
    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )

    chats = await client.get("/chats", headers={"X-User-Id": sender_id})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["last_message"]["kind"] == "service"
    assert chat["last_message"]["service_action"] == "message_pinned"
    assert chat["last_message"]["service_target_message_id"] == message_id


async def test_cannot_edit_a_service_message(client: AsyncClient):
    """Service messages can never be edited, even by whoever triggered them."""
    sender_id = str(uuid4())
    chat_id, message_id, _ = await _create_chat_with_message(
        client, sender_id, "important"
    )
    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    history = await _history(client, chat_id, sender_id)
    service_message_id = next(m["id"] for m in history if m["kind"] == "service")

    resp = await client.patch(
        f"/chats/{chat_id}/messages/{service_message_id}",
        json={"body": "hacked"},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 400


async def test_cannot_reply_to_a_service_message(client: AsyncClient):
    """Replying to a service message is rejected."""
    sender_id = str(uuid4())
    chat_id, message_id, _ = await _create_chat_with_message(
        client, sender_id, "important"
    )
    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    history = await _history(client, chat_id, sender_id)
    service_message_id = next(m["id"] for m in history if m["kind"] == "service")

    resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "replying to a service message",
            "client_msg_id": str(uuid4()),
            "reply_to_message_id": service_message_id,
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 400


async def test_cannot_forward_a_service_message(client: AsyncClient):
    """Forwarding a service message as the source is rejected."""
    sender_id = str(uuid4())
    chat_id, message_id, _ = await _create_chat_with_message(
        client, sender_id, "important"
    )
    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    history = await _history(client, chat_id, sender_id)
    service_message_id = next(m["id"] for m in history if m["kind"] == "service")

    target_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    target_chat_id = target_chat_resp.json()["id"]

    resp = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json={
            "source_chat_id": chat_id,
            "source_message_ids": [service_message_id],
            "client_msg_id": str(uuid4()),
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 400
