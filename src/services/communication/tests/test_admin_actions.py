"""Tests for the admin-only internal actions.

Covers offboarding, notifications chats, broadcast, and the message-based
file-access check all of these rest on.
"""

from uuid import UUID, uuid4

from httpx import AsyncClient

from app.chats.models import Chat


async def _create_group(client: AsyncClient, owner: str, members=(), title="Team"):
    response = await client.post(
        "/chats/group",
        headers={"X-User-Id": owner},
        json={"title": title, "member_ids": list(members)},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _roles(client: AsyncClient, chat_id: str, actor: str) -> dict[str, str]:
    response = await client.get(
        f"/chats/{chat_id}/members", headers={"X-User-Id": actor}
    )
    assert response.status_code == 200, response.text
    return {member["user_id"]: member["role"] for member in response.json()}


# --- notifications chat: get-or-create, listing, read-only guard ----------


async def test_ensure_notifications_chat_is_idempotent(client: AsyncClient):
    """Calling it twice for the same user returns the same chat id."""
    user_id = str(uuid4())

    first = await client.post(f"/internal/users/{user_id}/notifications-chat")
    second = await client.post(f"/internal/users/{user_id}/notifications-chat")

    assert first.status_code == 200
    assert first.json()["chat_id"] == second.json()["chat_id"]


async def test_notifications_chat_appears_in_the_users_chat_list(client: AsyncClient):
    """The chat shows up with the fixed display name "Уведомления"."""
    user_id = str(uuid4())
    created = await client.post(f"/internal/users/{user_id}/notifications-chat")
    chat_id = created.json()["chat_id"]

    chats = await client.get("/chats", headers={"X-User-Id": user_id})

    assert chats.status_code == 200
    [chat] = [c for c in chats.json() if c["id"] == chat_id]
    assert chat["type"] == "notifications"
    assert chat["title"] == "Уведомления"


async def test_cannot_send_a_message_into_a_notifications_chat(client: AsyncClient):
    """Not even the chat's own member can write into it the normal way."""
    user_id = str(uuid4())
    created = await client.post(f"/internal/users/{user_id}/notifications-chat")
    chat_id = created.json()["chat_id"]

    resp = await client.post(
        f"/chats/{chat_id}/messages",
        headers={"X-User-Id": user_id},
        json={"body": "hello", "client_msg_id": str(uuid4())},
    )

    assert resp.status_code == 403


# --- broadcast --------------------------------------------------------------


async def test_broadcast_to_specific_users_creates_their_chats_and_messages(
    client: AsyncClient,
):
    """Each target user gets their own chat with their own copy of the message."""
    admin_id = str(uuid4())
    alice = str(uuid4())
    bob = str(uuid4())

    resp = await client.post(
        "/internal/broadcast",
        json={
            "sender_id": admin_id,
            "body": "Плановые работы в 20:00",
            "user_ids": [alice, bob],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["recipient_count"] == 2

    for user_id in (alice, bob):
        chats = await client.get("/chats", headers={"X-User-Id": user_id})
        [notif_chat] = [c for c in chats.json() if c["type"] == "notifications"]
        assert notif_chat["last_message"]["body"] == "Плановые работы в 20:00"
        assert notif_chat["last_message"]["sender_id"] == admin_id


async def test_broadcast_reuses_an_already_existing_notifications_chat(
    client: AsyncClient,
):
    """A repeat recipient gets the new message in their existing chat.

    Not a second notifications chat, even across two separate broadcasts.
    """
    admin_id = str(uuid4())
    user_id = str(uuid4())
    existing = await client.post(f"/internal/users/{user_id}/notifications-chat")
    existing_chat_id = existing.json()["chat_id"]

    await client.post(
        "/internal/broadcast",
        json={"sender_id": admin_id, "body": "second message", "user_ids": [user_id]},
    )

    chats = await client.get("/chats", headers={"X-User-Id": user_id})
    notif_chats = [c for c in chats.json() if c["type"] == "notifications"]
    assert len(notif_chats) == 1
    assert notif_chats[0]["id"] == existing_chat_id


async def test_broadcast_attaches_the_same_file_to_every_recipients_message(
    client: AsyncClient,
):
    """One file_id, reused across every recipient's own message — no re-upload."""
    admin_id = str(uuid4())
    alice = str(uuid4())
    bob = str(uuid4())
    file_id = str(uuid4())

    await client.post(
        "/internal/broadcast",
        json={
            "sender_id": admin_id,
            "body": "see attached",
            "attachment_file_ids": [file_id],
            "user_ids": [alice, bob],
        },
    )

    for user_id in (alice, bob):
        access = await client.get(f"/internal/files/{file_id}/access/{user_id}")
        assert access.json()["authorized"] is True

    stranger = str(uuid4())
    access = await client.get(f"/internal/files/{file_id}/access/{stranger}")
    assert access.json()["authorized"] is False


async def test_broadcast_with_no_user_ids_targets_every_known_user(
    client: AsyncClient, mock_identity_service
):
    """None (absent) user_ids means everyone — enumerated via identity."""
    admin_id = str(uuid4())
    everyone = [str(uuid4()), str(uuid4()), str(uuid4())]

    def _fake_accounts(url, **kwargs):
        from httpx import Request, Response

        if url.endswith("/internal/accounts") and kwargs.get("params", {}).get(
            "offset"
        ) == 0:
            return Response(
                200,
                json=[{"id": uid} for uid in everyone],
                request=Request("GET", url),
            )
        return Response(200, json=[], request=Request("GET", url))

    mock_identity_service.return_value.get.side_effect = _fake_accounts

    resp = await client.post(
        "/internal/broadcast", json={"sender_id": admin_id, "body": "to everyone"}
    )

    assert resp.json()["recipient_count"] == len(everyone)


# --- offboarding: cascade delete -------------------------------------------


async def test_offboard_deletes_the_users_direct_chats(client: AsyncClient):
    """A 1:1 chat is hard-deleted entirely, not just the membership row."""
    alice = str(uuid4())
    bob = str(uuid4())
    created = await client.post(
        "/chats/direct", headers={"X-User-Id": alice}, json={"peer_user_id": bob}
    )
    chat_id = created.json()["id"]
    await client.post(
        f"/chats/{chat_id}/messages",
        headers={"X-User-Id": alice},
        json={"body": "hi", "client_msg_id": str(uuid4())},
    )

    resp = await client.post(f"/internal/users/{alice}/offboard")
    assert resp.status_code == 204

    bobs_chats = await client.get("/chats", headers={"X-User-Id": bob})
    assert all(c["id"] != chat_id for c in bobs_chats.json())


async def test_offboard_removes_plain_group_membership_but_keeps_the_group(
    client: AsyncClient,
):
    """A departing plain member just leaves — the group survives for the rest."""
    owner = str(uuid4())
    leaving = str(uuid4())
    staying = str(uuid4())
    chat_id = await _create_group(client, owner, members=[leaving, staying])

    resp = await client.post(f"/internal/users/{leaving}/offboard")
    assert resp.status_code == 204

    roles = await _roles(client, chat_id, owner)
    assert leaving not in roles
    assert roles[owner] == "owner"
    assert roles[staying] == "member"


async def test_offboard_transfers_ownership_to_the_oldest_remaining_member(
    client: AsyncClient,
):
    """Deleting the owner hands the group to the longest-tenured member."""
    owner = str(uuid4())
    earlier_member = str(uuid4())
    later_member = str(uuid4())
    chat_id = await _create_group(client, owner, members=[earlier_member])

    # A second member added afterwards joins later than the first.
    await client.post(
        f"/chats/{chat_id}/members",
        headers={"X-User-Id": owner},
        json={"user_ids": [later_member]},
    )

    resp = await client.post(f"/internal/users/{owner}/offboard")
    assert resp.status_code == 204

    roles = await _roles(client, chat_id, earlier_member)
    assert owner not in roles
    assert roles[earlier_member] == "owner"
    assert roles[later_member] == "member"


async def test_offboard_deletes_a_group_left_with_no_members(
    client: AsyncClient, db_session_maker
):
    """The sole member (owner) leaving via offboard removes the empty group too."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner)

    resp = await client.post(f"/internal/users/{owner}/offboard")
    assert resp.status_code == 204

    async with db_session_maker() as db:
        assert await db.get(Chat, UUID(chat_id)) is None
