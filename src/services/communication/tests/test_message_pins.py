"""Tests for pinning messages within a chat (personal and chat-wide scopes)."""

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


async def _pinned_ids(client: AsyncClient, chat_id: str, user_id: str) -> list[str]:
    resp = await client.get(
        f"/chats/{chat_id}/messages/pinned", headers={"X-User-Id": user_id}
    )
    assert resp.status_code == 200
    return [m["id"] for m in resp.json()]


async def test_pin_for_everyone_is_visible_to_every_member(client: AsyncClient):
    """A message pinned "for everyone" shows up in every member's pinned list."""
    sender_id = str(uuid4())
    chat_id, message_id, peer_id = await _create_chat_with_message(
        client, sender_id, "important"
    )

    resp = await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 204

    assert message_id in await _pinned_ids(client, chat_id, sender_id)
    assert message_id in await _pinned_ids(client, chat_id, peer_id)


async def test_pin_for_me_is_only_visible_to_the_pinner(client: AsyncClient):
    """A personal pin doesn't show up for other chat members."""
    sender_id = str(uuid4())
    chat_id, message_id, peer_id = await _create_chat_with_message(
        client, sender_id, "just for me"
    )

    resp = await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "me"},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 204

    assert message_id in await _pinned_ids(client, chat_id, sender_id)
    assert message_id not in await _pinned_ids(client, chat_id, peer_id)


async def test_any_member_can_pin_in_any_chat_type(client: AsyncClient):
    """Pinning isn't restricted to the sender or a group owner."""
    sender_id = str(uuid4())
    chat_id, message_id, peer_id = await _create_chat_with_message(
        client, sender_id, "hi"
    )

    resp = await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": peer_id},
    )
    assert resp.status_code == 204
    assert message_id in await _pinned_ids(client, chat_id, sender_id)


async def test_unpin_for_me_on_a_global_pin_only_hides_it_for_that_user(
    client: AsyncClient,
):
    """Unpinning "for me" on a chat-wide pin doesn't affect other members."""
    sender_id = str(uuid4())
    chat_id, message_id, peer_id = await _create_chat_with_message(
        client, sender_id, "shared pin"
    )
    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )

    resp = await client.request(
        "DELETE",
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "me"},
        headers={"X-User-Id": peer_id},
    )
    assert resp.status_code == 204

    assert message_id not in await _pinned_ids(client, chat_id, peer_id)
    assert message_id in await _pinned_ids(client, chat_id, sender_id)


async def test_unpin_for_everyone_removes_it_for_every_member(client: AsyncClient):
    """Unpinning "for everyone" removes the chat-wide pin entirely."""
    sender_id = str(uuid4())
    chat_id, message_id, peer_id = await _create_chat_with_message(
        client, sender_id, "shared pin"
    )
    await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )

    resp = await client.request(
        "DELETE",
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": peer_id},
    )
    assert resp.status_code == 204

    assert message_id not in await _pinned_ids(client, chat_id, sender_id)
    assert message_id not in await _pinned_ids(client, chat_id, peer_id)


async def test_pin_message_forbidden_for_outsider(client: AsyncClient):
    """A user outside the chat cannot pin a message in it."""
    sender_id = str(uuid4())
    chat_id, message_id, _ = await _create_chat_with_message(client, sender_id, "hi")
    outsider = str(uuid4())

    resp = await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": outsider},
    )
    assert resp.status_code == 403


async def test_pin_nonexistent_message_returns_404(client: AsyncClient):
    """Pinning a message id that doesn't exist in the chat fails with 404."""
    sender_id = str(uuid4())
    chat_id, _, _ = await _create_chat_with_message(client, sender_id, "hi")

    resp = await client.post(
        f"/chats/{chat_id}/messages/{uuid4()}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 404


async def test_pinning_twice_for_everyone_is_idempotent(
    client: AsyncClient, mock_nats_client
):
    """Pinning an already-globally-pinned message again doesn't duplicate the row."""
    sender_id = str(uuid4())
    chat_id, message_id, _ = await _create_chat_with_message(client, sender_id, "hi")

    first = await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    second = await client.post(
        f"/chats/{chat_id}/messages/{message_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )
    assert first.status_code == 204
    assert second.status_code == 204
    assert await _pinned_ids(client, chat_id, sender_id) == [message_id]


async def test_pinned_list_reports_scope_per_message(client: AsyncClient):
    """The pinned-messages list tags each entry with "me" or "everyone"."""
    sender_id = str(uuid4())
    chat_id, _, _ = await _create_chat_with_message(client, sender_id, "first")

    personal_resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "personal", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    global_resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "global", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    personal_id = personal_resp.json()["id"]
    global_id = global_resp.json()["id"]

    await client.post(
        f"/chats/{chat_id}/messages/{personal_id}/pin",
        json={"scope": "me"},
        headers={"X-User-Id": sender_id},
    )
    await client.post(
        f"/chats/{chat_id}/messages/{global_id}/pin",
        json={"scope": "everyone"},
        headers={"X-User-Id": sender_id},
    )

    resp = await client.get(
        f"/chats/{chat_id}/messages/pinned", headers={"X-User-Id": sender_id}
    )
    scope_by_id = {m["id"]: m["pin_scope"] for m in resp.json()}
    assert scope_by_id[personal_id] == "me"
    assert scope_by_id[global_id] == "everyone"
