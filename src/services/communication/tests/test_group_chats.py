"""Integration tests for group access, memberships, and sync notifications."""

from uuid import uuid4

import pytest
from httpx import AsyncClient, Request, Response


async def _create_group(client, owner, members=(), title="Project team"):
    response = await client.post(
        "/chats/group",
        headers={"X-User-Id": owner},
        json={"title": title, "member_ids": list(members)},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _members(client, chat_id, actor):
    response = await client.get(
        f"/chats/{chat_id}/members", headers={"X-User-Id": actor}
    )
    assert response.status_code == 200, response.text
    return {member["user_id"]: member["role"] for member in response.json()}


def _assert_sync(publisher, chat_id, reason, recipients):
    publisher.assert_awaited_once_with(
        "chat.sync_required",
        {
            "chat_id": chat_id,
            "reason": reason,
            "recipient_ids": sorted(recipients),
        },
    )


async def test_create_solo_group(
    client: AsyncClient, mock_identity_service, mock_nats_client
):
    """A group can start with only its owner and no Identity request."""
    owner = str(uuid4())
    response = await client.post(
        "/chats/group",
        headers={"X-User-Id": owner},
        json={"title": "  My group  "},
    )
    assert response.status_code == 201
    chat_id = response.json()["id"]
    assert await _members(client, chat_id, owner) == {owner: "owner"}
    mock_identity_service.return_value.get.assert_not_awaited()
    _assert_sync(mock_nats_client, chat_id, "created", [owner])

    chats = await client.get("/chats", headers={"X-User-Id": owner})
    assert chats.json() == [
        {
            "id": chat_id,
            "type": "group",
            "title": "My group",
            "last_message": None,
            "unread_count": 0,
        }
    ]


async def test_group_creation_normalizes_members(client: AsyncClient, mock_nats_client):
    """Creator and repeated ids produce one membership per user."""
    owner, member, other = [str(uuid4()) for _ in range(3)]
    chat_id = await _create_group(client, owner, [owner, member, member, other])
    assert await _members(client, chat_id, member) == {
        owner: "owner",
        member: "member",
        other: "member",
    }
    _assert_sync(mock_nats_client, chat_id, "created", [owner, member, other])

    second_id = await _create_group(client, owner, [member, other])
    assert second_id != chat_id


async def test_group_title_max_length(client: AsyncClient):
    """The inclusive 128-character title boundary is accepted."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner, title="a" * 128)
    response = await client.get("/chats", headers={"X-User-Id": owner})
    assert response.json()[0]["id"] == chat_id
    assert response.json()[0]["title"] == "a" * 128


@pytest.mark.parametrize("title,status", [("", 422), (" " * 3, 400), ("a" * 129, 422)])
async def test_invalid_group_title(
    client: AsyncClient, mock_nats_client, title, status
):
    """Invalid names neither persist a chat nor publish a notification."""
    owner = str(uuid4())
    response = await client.post(
        "/chats/group", headers={"X-User-Id": owner}, json={"title": title}
    )
    assert response.status_code == status
    mock_nats_client.assert_not_awaited()
    chats = await client.get("/chats", headers={"X-User-Id": owner})
    assert chats.json() == []


@pytest.mark.parametrize("operation", ["create", "add"])
async def test_missing_group_user_is_atomic(
    client: AsyncClient, mock_identity_service, mock_nats_client, operation
):
    """One missing invitee prevents adding any users or publishing an event."""
    owner, valid, missing = [str(uuid4()) for _ in range(3)]
    chat_id = await _create_group(client, owner) if operation == "add" else None
    mock_nats_client.reset_mock()
    mock_identity_service.return_value.get.side_effect = None
    mock_identity_service.return_value.get.return_value = Response(
        200, json=[{"id": valid}], request=Request("GET", "http://identity/users")
    )
    if operation == "create":
        response = await client.post(
            "/chats/group",
            headers={"X-User-Id": owner},
            json={"title": "Group", "member_ids": [valid, missing]},
        )
        chats = await client.get("/chats", headers={"X-User-Id": owner})
        assert chats.json() == []
    else:
        response = await client.post(
            f"/chats/{chat_id}/members",
            headers={"X-User-Id": owner},
            json={"user_ids": [valid, missing]},
        )
        assert await _members(client, chat_id, owner) == {owner: "owner"}
    assert response.status_code == 404
    mock_nats_client.assert_not_awaited()


async def test_mixed_chat_list_and_privacy(client: AsyncClient):
    """One list includes both chat types without exposing an unrelated group."""
    owner, member, outsider = [str(uuid4()) for _ in range(3)]
    group_id = await _create_group(client, owner, [member], title="Team")
    direct = await client.post(
        "/chats/direct",
        headers={"X-User-Id": owner},
        json={"peer_user_id": member},
    )
    assert direct.status_code == 201
    chats = await client.get("/chats", headers={"X-User-Id": owner})
    by_id = {chat["id"]: chat for chat in chats.json()}
    assert set(by_id) == {group_id, direct.json()["id"]}
    assert by_id[group_id]["type"] == "group"
    assert by_id[group_id]["title"] == "Team"
    assert by_id[direct.json()["id"]]["type"] == "direct"
    assert by_id[direct.json()["id"]]["title"] is None
    private = await client.get("/chats", headers={"X-User-Id": outsider})
    assert private.json() == []


async def test_add_members_is_idempotent(client: AsyncClient, mock_nats_client):
    """Retries keep one membership per user and never demote the owner."""
    owner, member, added = [str(uuid4()) for _ in range(3)]
    chat_id = await _create_group(client, owner, [member])
    for _ in range(2):
        mock_nats_client.reset_mock()
        response = await client.post(
            f"/chats/{chat_id}/members",
            headers={"X-User-Id": owner},
            json={"user_ids": [added, added, member, owner]},
        )
        assert response.status_code == 204
        assert response.content == b""
        assert await _members(client, chat_id, owner) == {
            owner: "owner",
            member: "member",
            added: "member",
        }
        _assert_sync(mock_nats_client, chat_id, "members_added", [owner, member, added])


@pytest.mark.parametrize("operation", ["add", "remove", "rename"])
@pytest.mark.parametrize("actor_role", ["member", "outsider"])
async def test_group_management_requires_owner(
    client: AsyncClient, mock_nats_client, operation, actor_role
):
    """Non-owners cannot mutate another user's group or membership."""
    owner, member, target, outsider = [str(uuid4()) for _ in range(4)]
    chat_id = await _create_group(client, owner, [member, target])
    actor = member if actor_role == "member" else outsider
    mock_nats_client.reset_mock()
    headers = {"X-User-Id": actor}
    if operation == "add":
        response = await client.post(
            f"/chats/{chat_id}/members",
            headers=headers,
            json={"user_ids": [outsider]},
        )
    elif operation == "remove":
        response = await client.delete(
            f"/chats/{chat_id}/members/{target}", headers=headers
        )
    else:
        response = await client.patch(
            f"/chats/{chat_id}", headers=headers, json={"title": "Hijacked"}
        )
    assert response.status_code == 403
    mock_nats_client.assert_not_awaited()
    assert await _members(client, chat_id, owner) == {
        owner: "owner",
        member: "member",
        target: "member",
    }
    chats = await client.get("/chats", headers={"X-User-Id": owner})
    assert chats.json()[0]["title"] == "Project team"


@pytest.mark.parametrize("operation", ["add", "remove", "rename"])
async def test_direct_chat_rejects_group_operations(
    client: AsyncClient, mock_nats_client, operation
):
    """A direct chat cannot be renamed or have its membership changed."""
    owner, member = [str(uuid4()) for _ in range(2)]
    direct = await client.post(
        "/chats/direct",
        headers={"X-User-Id": owner},
        json={"peer_user_id": member},
    )
    chat_id = direct.json()["id"]
    mock_nats_client.reset_mock()
    headers = {"X-User-Id": owner}
    if operation == "add":
        response = await client.post(
            f"/chats/{chat_id}/members",
            headers=headers,
            json={"user_ids": [str(uuid4())]},
        )
    elif operation == "remove":
        response = await client.delete(
            f"/chats/{chat_id}/members/{owner}", headers=headers
        )
    else:
        response = await client.patch(
            f"/chats/{chat_id}", headers=headers, json={"title": "Group"}
        )
    assert response.status_code == 409
    mock_nats_client.assert_not_awaited()
    assert set(await _members(client, chat_id, owner)) == {owner, member}


@pytest.mark.parametrize("self_leave", [False, True])
async def test_removed_member_loses_access_and_receives_sync(
    client: AsyncClient, mock_nats_client, self_leave
):
    """Removal notifies all affected users and revokes the removed user's access."""
    owner, member, other = [str(uuid4()) for _ in range(3)]
    chat_id = await _create_group(client, owner, [member, other])
    before = await client.post(
        f"/chats/{chat_id}/messages",
        headers={"X-User-Id": owner},
        json={"body": "Before removal", "client_msg_id": str(uuid4())},
    )
    assert before.status_code == 201
    mock_nats_client.reset_mock()
    actor = member if self_leave else owner
    response = await client.delete(
        f"/chats/{chat_id}/members/{member}", headers={"X-User-Id": actor}
    )
    assert response.status_code == 204
    _assert_sync(mock_nats_client, chat_id, "member_removed", [owner, member, other])
    assert await _members(client, chat_id, owner) == {owner: "owner", other: "member"}

    mock_nats_client.reset_mock()
    repeated = await client.delete(
        f"/chats/{chat_id}/members/{member}", headers={"X-User-Id": actor}
    )
    assert repeated.status_code == 204
    mock_nats_client.assert_not_awaited()

    headers = {"X-User-Id": member}
    chats = await client.get("/chats", headers=headers)
    assert chats.json() == []
    for path in ("messages?limit=10", "members"):
        forbidden = await client.get(f"/chats/{chat_id}/{path}", headers=headers)
        assert forbidden.status_code == 403
    forbidden_send = await client.post(
        f"/chats/{chat_id}/messages",
        headers=headers,
        json={"body": "Forbidden", "client_msg_id": str(uuid4())},
    )
    assert forbidden_send.status_code == 403
    mock_nats_client.assert_not_awaited()

    after = await client.post(
        f"/chats/{chat_id}/messages",
        headers={"X-User-Id": owner},
        json={"body": "After removal", "client_msg_id": str(uuid4())},
    )
    assert after.status_code == 201
    payload = mock_nats_client.await_args.args[1]
    assert set(payload["recipient_ids"]) == {owner, other}


async def test_owner_cannot_leave(client: AsyncClient, mock_nats_client):
    """The sole owner cannot orphan the group by leaving."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner)
    mock_nats_client.reset_mock()
    response = await client.delete(
        f"/chats/{chat_id}/members/{owner}", headers={"X-User-Id": owner}
    )
    assert response.status_code == 409
    assert await _members(client, chat_id, owner) == {owner: "owner"}
    mock_nats_client.assert_not_awaited()


async def test_group_membership_updates_presence_peers(client: AsyncClient):
    """A peer disappears only after the last shared chat membership is removed."""
    owner, member, other = [str(uuid4()) for _ in range(3)]
    first = await _create_group(client, owner, [member, other])
    second = await _create_group(client, owner, [member])

    async def peer_ids(user_id):
        response = await client.get(f"/internal/users/{user_id}/chat-peers")
        assert response.status_code == 200
        return response.json()["user_ids"]

    assert await peer_ids(owner) == sorted([member, other])
    assert await peer_ids(member) == sorted([owner, other])
    for chat_id in (first, second):
        response = await client.delete(
            f"/chats/{chat_id}/members/{member}", headers={"X-User-Id": owner}
        )
        assert response.status_code == 204
        if chat_id == first:
            assert await peer_ids(owner) == sorted([member, other])
            assert await peer_ids(member) == [owner]
    assert await peer_ids(owner) == [other]
    assert await peer_ids(member) == []


async def test_empty_member_addition_is_rejected(client: AsyncClient, mock_nats_client):
    """An empty addition is invalid and must not trigger a sync."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner)
    mock_nats_client.reset_mock()
    response = await client.post(
        f"/chats/{chat_id}/members",
        headers={"X-User-Id": owner},
        json={"user_ids": []},
    )
    assert response.status_code == 422
    assert await _members(client, chat_id, owner) == {owner: "owner"}
    mock_nats_client.assert_not_awaited()


async def test_rename_group(client: AsyncClient, mock_nats_client):
    """A rename trims whitespace, persists the title, and notifies all members."""
    owner, member = [str(uuid4()) for _ in range(2)]
    chat_id = await _create_group(client, owner, [member])
    mock_nats_client.reset_mock()
    response = await client.patch(
        f"/chats/{chat_id}",
        headers={"X-User-Id": owner},
        json={"title": "  New name  "},
    )
    assert response.status_code == 204
    assert response.content == b""
    _assert_sync(mock_nats_client, chat_id, "updated", [owner, member])
    chats = await client.get("/chats", headers={"X-User-Id": member})
    assert chats.json()[0]["title"] == "New name"


@pytest.mark.parametrize("title,status", [("", 422), ("   ", 400), ("a" * 129, 422)])
async def test_invalid_rename(client: AsyncClient, mock_nats_client, title, status):
    """A rejected rename leaves the old title and publishes no event."""
    owner = str(uuid4())
    chat_id = await _create_group(client, owner)
    mock_nats_client.reset_mock()
    response = await client.patch(
        f"/chats/{chat_id}", headers={"X-User-Id": owner}, json={"title": title}
    )
    assert response.status_code == status
    mock_nats_client.assert_not_awaited()
    chats = await client.get("/chats", headers={"X-User-Id": owner})
    assert chats.json()[0]["title"] == "Project team"


async def test_group_message_fanout_and_unread(client: AsyncClient, mock_nats_client):
    """Messages reach every current member and are unread only for other users."""
    owner, member, other = [str(uuid4()) for _ in range(3)]
    chat_id = await _create_group(client, owner, [member, other])
    mock_nats_client.reset_mock()
    message = await client.post(
        f"/chats/{chat_id}/messages",
        headers={"X-User-Id": member},
        json={"body": "Hello group", "client_msg_id": str(uuid4())},
    )
    assert message.status_code == 201
    assert mock_nats_client.await_args.args[0] == "chat.message.created"
    assert set(mock_nats_client.await_args.args[1]["recipient_ids"]) == {
        owner,
        member,
        other,
    }
    for user_id in (owner, member, other):
        chats = await client.get("/chats", headers={"X-User-Id": user_id})
        chat = chats.json()[0]
        assert chat["last_message"]["body"] == "Hello group"
        assert chat["unread_count"] == (0 if user_id == member else 1)


async def test_group_publish_happens_after_persistence(
    client: AsyncClient, mock_nats_client
):
    """A publish failure occurs after durable creation, documenting the delivery gap."""
    owner = str(uuid4())
    mock_nats_client.side_effect = RuntimeError("NATS unavailable")
    with pytest.raises(RuntimeError, match="NATS unavailable"):
        await client.post(
            "/chats/group", headers={"X-User-Id": owner}, json={"title": "Saved"}
        )
    chats = await client.get("/chats", headers={"X-User-Id": owner})
    assert len(chats.json()) == 1
    assert chats.json()[0]["title"] == "Saved"
