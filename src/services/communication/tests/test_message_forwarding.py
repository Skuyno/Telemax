"""Tests for forwarding one or more messages from one chat into another."""

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
        json={
            "body": body,
            "client_msg_id": str(uuid4()),
            "attachment_file_ids": [],
        },
        headers={"X-User-Id": sender_id},
    )
    return chat_id, msg_resp.json()["id"]


async def test_forward_message_copies_body_and_attribution(client: AsyncClient):
    """The forwarded copy carries the original text and sender attribution."""
    sender_id = str(uuid4())
    source_chat_id, source_message_id = await _create_chat_with_message(
        client, sender_id, "original text"
    )
    target_peer_id = str(uuid4())
    target_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": target_peer_id},
        headers={"X-User-Id": sender_id},
    )
    target_chat_id = target_chat_resp.json()["id"]

    resp = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json={
            "source_chat_id": source_chat_id,
            "source_message_ids": [source_message_id],
            "client_msg_id": str(uuid4()),
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 201
    messages = resp.json()
    assert len(messages) == 1
    body = messages[0]
    assert body["body"] == "original text"
    assert body["chat_id"] == target_chat_id
    assert body["forwarded_from_message_id"] == source_message_id
    assert body["forwarded_from_sender_id"] == sender_id

    # The new message is independent — editing the original doesn't touch it.
    await client.patch(
        f"/chats/{source_chat_id}/messages/{source_message_id}",
        json={"body": "edited original"},
        headers={"X-User-Id": sender_id},
    )
    forwarded = await client.get(
        f"/chats/{target_chat_id}/messages?limit=10", headers={"X-User-Id": sender_id}
    )
    assert forwarded.json()[0]["body"] == "original text"


async def test_forward_multiple_messages_preserves_original_order(client: AsyncClient):
    """Several messages forwarded at once keep their original chat's order."""
    sender_id = str(uuid4())
    source_chat_id, first_id = await _create_chat_with_message(client, sender_id, "one")
    second = await client.post(
        f"/chats/{source_chat_id}/messages",
        json={"body": "two", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    third = await client.post(
        f"/chats/{source_chat_id}/messages",
        json={"body": "three", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    second_id = second.json()["id"]
    third_id = third.json()["id"]

    target_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    target_chat_id = target_chat_resp.json()["id"]

    # Deliberately requested out of order.
    resp = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json={
            "source_chat_id": source_chat_id,
            "source_message_ids": [third_id, first_id, second_id],
            "client_msg_id": str(uuid4()),
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 201
    assert [m["body"] for m in resp.json()] == ["one", "two", "three"]


async def test_forward_message_copies_attachments(client: AsyncClient):
    """Forwarding copies the original message's attachment file ids."""
    sender_id = str(uuid4())
    peer_id = str(uuid4())
    chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": peer_id},
        headers={"X-User-Id": sender_id},
    )
    source_chat_id = chat_resp.json()["id"]
    file_id = str(uuid4())
    msg_resp = await client.post(
        f"/chats/{source_chat_id}/messages",
        json={
            "body": "photo",
            "client_msg_id": str(uuid4()),
            "attachment_file_ids": [file_id],
        },
        headers={"X-User-Id": sender_id},
    )
    source_message_id = msg_resp.json()["id"]

    target_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    target_chat_id = target_chat_resp.json()["id"]

    resp = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json={
            "source_chat_id": source_chat_id,
            "source_message_ids": [source_message_id],
            "client_msg_id": str(uuid4()),
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.json()[0]["attachment_file_ids"] == [file_id]


async def test_forward_requires_membership_in_source_chat(client: AsyncClient):
    """A user who can't see the source chat can't forward from it."""
    sender_id = str(uuid4())
    source_chat_id, source_message_id = await _create_chat_with_message(
        client, sender_id, "secret"
    )
    outsider = str(uuid4())
    target_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(uuid4())},
        headers={"X-User-Id": outsider},
    )
    target_chat_id = target_chat_resp.json()["id"]

    resp = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json={
            "source_chat_id": source_chat_id,
            "source_message_ids": [source_message_id],
            "client_msg_id": str(uuid4()),
        },
        headers={"X-User-Id": outsider},
    )
    assert resp.status_code == 403


async def test_forward_requires_membership_in_target_chat(client: AsyncClient):
    """A user can't forward into a chat they don't belong to."""
    sender_id = str(uuid4())
    source_chat_id, source_message_id = await _create_chat_with_message(
        client, sender_id, "hello"
    )
    other_peer_a = str(uuid4())
    other_peer_b = str(uuid4())
    other_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": other_peer_b},
        headers={"X-User-Id": other_peer_a},
    )
    target_chat_id = other_chat_resp.json()["id"]

    resp = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json={
            "source_chat_id": source_chat_id,
            "source_message_ids": [source_message_id],
            "client_msg_id": str(uuid4()),
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 403


async def test_forward_deleted_message_returns_404(client: AsyncClient):
    """A deleted source message can no longer be forwarded."""
    sender_id = str(uuid4())
    source_chat_id, source_message_id = await _create_chat_with_message(
        client, sender_id, "gone soon"
    )
    await client.delete(
        f"/chats/{source_chat_id}/messages/{source_message_id}",
        headers={"X-User-Id": sender_id},
    )
    target_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    target_chat_id = target_chat_resp.json()["id"]

    resp = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json={
            "source_chat_id": source_chat_id,
            "source_message_ids": [source_message_id],
            "client_msg_id": str(uuid4()),
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 404


async def test_forward_rejects_whole_batch_if_any_message_is_invalid(
    client: AsyncClient,
):
    """One bad id in the batch means nothing gets forwarded at all."""
    sender_id = str(uuid4())
    source_chat_id, valid_id = await _create_chat_with_message(client, sender_id, "ok")
    target_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    target_chat_id = target_chat_resp.json()["id"]

    resp = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json={
            "source_chat_id": source_chat_id,
            "source_message_ids": [valid_id, str(uuid4())],
            "client_msg_id": str(uuid4()),
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 404

    history = await client.get(
        f"/chats/{target_chat_id}/messages?limit=10", headers={"X-User-Id": sender_id}
    )
    assert history.json() == []


async def test_retrying_forward_with_same_client_msg_id_is_idempotent(
    client: AsyncClient,
):
    """Resending the same forward request returns the same message, not a duplicate."""
    sender_id = str(uuid4())
    source_chat_id, source_message_id = await _create_chat_with_message(
        client, sender_id, "hi"
    )
    target_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(uuid4())},
        headers={"X-User-Id": sender_id},
    )
    target_chat_id = target_chat_resp.json()["id"]
    client_msg_id = str(uuid4())
    payload = {
        "source_chat_id": source_chat_id,
        "source_message_ids": [source_message_id],
        "client_msg_id": client_msg_id,
    }

    first = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json=payload,
        headers={"X-User-Id": sender_id},
    )
    second = await client.post(
        f"/chats/{target_chat_id}/messages/forward",
        json=payload,
        headers={"X-User-Id": sender_id},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()[0]["id"] == second.json()[0]["id"]
