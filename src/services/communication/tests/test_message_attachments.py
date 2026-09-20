"""Tests for message attachments (file_id references validated by file-orchestrator)."""

from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import AsyncClient


async def _create_chat(client: AsyncClient, creator_id: str, peer_id: str) -> str:
    resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": peer_id},
        headers={"X-User-Id": creator_id},
    )
    return resp.json()["id"]


async def test_send_message_with_attachments(client: AsyncClient):
    """A message can carry attachment file ids, returned back in the response."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    file_id = str(uuid4())

    resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "check this out",
            "client_msg_id": str(uuid4()),
            "attachment_file_ids": [file_id],
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 201
    assert resp.json()["attachment_file_ids"] == [file_id]


async def test_get_chat_messages_includes_attachments(client: AsyncClient):
    """Attachment ids show up when listing message history too."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    file_id = str(uuid4())

    await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "photo",
            "client_msg_id": str(uuid4()),
            "attachment_file_ids": [file_id],
        },
        headers={"X-User-Id": sender_id},
    )

    resp = await client.get(
        f"/chats/{chat_id}/messages?limit=10", headers={"X-User-Id": sender_id}
    )
    assert resp.json()[0]["attachment_file_ids"] == [file_id]


async def test_send_message_rejects_invalid_attachment(
    client: AsyncClient, mock_identity_service
):
    """A file id file-orchestrator doesn't recognize is rejected with 400."""
    async def fake_post(*args, **kwargs):
        response = AsyncMock()
        response.raise_for_status = lambda: None
        response.json = lambda: {"valid_file_ids": []}
        return response

    mock_identity_service.return_value.post.side_effect = fake_post

    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))

    resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "nope",
            "client_msg_id": str(uuid4()),
            "attachment_file_ids": [str(uuid4())],
        },
        headers={"X-User-Id": sender_id},
    )
    assert resp.status_code == 400


async def test_retrying_send_does_not_duplicate_attachments(client: AsyncClient):
    """Resending the same client_msg_id doesn't fail on duplicate attachment links."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    file_id = str(uuid4())
    client_msg_id = str(uuid4())
    body = {
        "body": "retry me",
        "client_msg_id": client_msg_id,
        "attachment_file_ids": [file_id],
    }

    first = await client.post(
        f"/chats/{chat_id}/messages", json=body, headers={"X-User-Id": sender_id}
    )
    second = await client.post(
        f"/chats/{chat_id}/messages", json=body, headers={"X-User-Id": sender_id}
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["attachment_file_ids"] == [file_id]


async def test_delete_message_publishes_attachment_ids(
    client: AsyncClient, mock_nats_client
):
    """Deleting a message includes its attachment ids in the NATS event."""
    sender_id = str(uuid4())
    chat_id = await _create_chat(client, sender_id, str(uuid4()))
    file_id = str(uuid4())

    msg = await client.post(
        f"/chats/{chat_id}/messages",
        json={
            "body": "delete me",
            "client_msg_id": str(uuid4()),
            "attachment_file_ids": [file_id],
        },
        headers={"X-User-Id": sender_id},
    )
    message_id = msg.json()["id"]

    await client.delete(
        f"/chats/{chat_id}/messages/{message_id}", headers={"X-User-Id": sender_id}
    )

    delete_call = next(
        call
        for call in mock_nats_client.call_args_list
        if call.args[0] == "chat.message.deleted"
    )
    assert delete_call.args[1]["attachment_file_ids"] == [file_id]
