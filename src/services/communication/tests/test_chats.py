"""Tests for the chat endpoints."""

from uuid import UUID, uuid4

from httpx import AsyncClient


async def test_create_direct_chat_succes(client: AsyncClient):
    """Create a direct chat between two new users returns 201."""
    resp = await client.post(
        "/chats/direct",
        json={
            "peer_user_id": str(uuid4()),
        },
        headers={
            "X-User-Id": str(uuid4()),
        },
    )
    assert resp.status_code == 201


async def test_create_get_direct_chat_succes(client: AsyncClient):
    """Creating the same direct chat twice returns 201 then 200 with the same id."""
    p_u_id = str(uuid4())
    x_user_id = str(uuid4())

    first = await client.post(
        "/chats/direct",
        json={
            "peer_user_id": p_u_id,
        },
        headers={
            "X-User-Id": x_user_id,
        },
    )

    assert first.status_code == 201

    second = await client.post(
        "/chats/direct",
        json={
            "peer_user_id": p_u_id,
        },
        headers={
            "X-User-Id": x_user_id,
        },
    )

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


async def test_create_direct_chat_order_independent(client: AsyncClient):
    """Direct chat lookup ignores which user is creator vs peer."""
    p_u_id = str(uuid4())
    x_user_id = str(uuid4())

    first = await client.post(
        "/chats/direct",
        json={
            "peer_user_id": p_u_id,
        },
        headers={
            "X-User-Id": x_user_id,
        },
    )

    assert first.status_code == 201

    second = await client.post(
        "/chats/direct",
        json={
            "peer_user_id": x_user_id,
        },
        headers={
            "X-User-Id": p_u_id,
        },
    )

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


async def test_create_self_chat_success(client: AsyncClient):
    """Creating a chat with yourself as the peer returns 201."""
    x_user_id = str(uuid4())

    resp = await client.post(
        "/chats/direct",
        json={
            "peer_user_id": x_user_id,
        },
        headers={
            "X-User-Id": x_user_id,
        },
    )
    assert resp.status_code == 201


async def test_list_chats_empty(client: AsyncClient):
    """A user with no chats gets an empty list."""
    x_user_id = str(uuid4())

    resp = await client.get(
        "/chats",
        headers={
            "X-User-Id": x_user_id,
        },
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_chats_without_messages(client: AsyncClient):
    """A chat with no messages yet shows up with last_message set to null."""
    peer_user_id = str(uuid4())
    x_user_id = str(uuid4())

    create_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": peer_user_id},
        headers={"X-User-Id": x_user_id},
    )
    chat_id = create_resp.json()["id"]

    resp = await client.get("/chats", headers={"X-User-Id": x_user_id})

    assert resp.status_code == 200
    chats = resp.json()
    assert len(chats) == 1
    assert chats[0]["id"] == chat_id
    assert chats[0]["last_message"] is None


async def test_list_chats_returns_latest_message(client: AsyncClient):
    """The last_message preview is the most recent message, not just any one."""
    peer_user_id = uuid4()
    x_user_id = uuid4()

    create_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(peer_user_id)},
        headers={"X-User-Id": str(x_user_id)},
    )
    chat_id = UUID(create_resp.json()["id"])

    await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "first message", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": str(x_user_id)},
    )

    await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "latest message", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": str(x_user_id)},
    )

    resp = await client.get("/chats", headers={"X-User-Id": str(x_user_id)})

    assert resp.status_code == 200
    chats = resp.json()
    assert chats[0]["last_message"]["body"] == "latest message"


async def test_list_chats_last_message_not_mixed_between_chats(client: AsyncClient):
    """Each chat's preview is its own last message, not another chat's."""
    x_user_id = uuid4()
    first_peer = uuid4()
    second_peer = uuid4()

    first_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(first_peer)},
        headers={"X-User-Id": str(x_user_id)},
    )
    second_chat_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(second_peer)},
        headers={"X-User-Id": str(x_user_id)},
    )
    first_chat_id = UUID(first_chat_resp.json()["id"])
    second_chat_id = UUID(second_chat_resp.json()["id"])

    await client.post(
        f"/chats/{first_chat_id}/messages",
        json={"body": "from first chat", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": str(x_user_id)},
    )

    await client.post(
        f"/chats/{second_chat_id}/messages",
        json={"body": "from second chat", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": str(x_user_id)},
    )

    resp = await client.get("/chats", headers={"X-User-Id": str(x_user_id)})

    assert resp.status_code == 200
    chats_by_id = {UUID(chat["id"]): chat for chat in resp.json()}
    assert chats_by_id[first_chat_id]["last_message"]["body"] == "from first chat"
    assert chats_by_id[second_chat_id]["last_message"]["body"] == "from second chat"


async def test_list_chats_excludes_other_users_chats(client: AsyncClient):
    """A chat the user isn't a member of doesn't show up in their list."""
    someone = str(uuid4())
    someone_else = str(uuid4())
    outsider = str(uuid4())

    await client.post(
        "/chats/direct",
        json={"peer_user_id": someone_else},
        headers={"X-User-Id": someone},
    )

    resp = await client.get("/chats", headers={"X-User-Id": outsider})

    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_chat_messages_success(client: AsyncClient):
    """Chat members can fetch message history."""
    peer_user_id = str(uuid4())
    x_user_id = str(uuid4())

    create_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(peer_user_id)},
        headers={"X-User-Id": str(x_user_id)},
    )
    chat_id = create_resp.json()["id"]

    first_msg_resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "first message", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": str(x_user_id)},
    )

    second_msg_resp = await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "latest message", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": str(x_user_id)},
    )
    assert first_msg_resp.status_code == 201
    assert second_msg_resp.status_code == 201

    history_resp = await client.get(
        f"/chats/{chat_id}/messages?limit=10", headers={"X-User-Id": x_user_id}
    )

    assert history_resp.status_code == 200
    messages = history_resp.json()
    assert len(messages) == 2
    assert messages[0]["body"] == "latest message"


async def test_get_chat_messages_pagination(client: AsyncClient):
    """Cursor pagination using before_msg_id works correctly."""
    peer_user_id = str(uuid4())
    x_user_id = str(uuid4())

    create_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(peer_user_id)},
        headers={"X-User-Id": str(x_user_id)},
    )
    chat_id = create_resp.json()["id"]

    await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "first message", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": str(x_user_id)},
    )

    await client.post(
        f"/chats/{chat_id}/messages",
        json={"body": "latest message", "client_msg_id": str(uuid4())},
        headers={"X-User-Id": str(x_user_id)},
    )

    resp1 = await client.get(
        f"/chats/{chat_id}/messages?limit=1",
        headers={"X-User-Id": x_user_id},
    )
    assert resp1.status_code == 200
    msgs1 = resp1.json()
    assert len(msgs1) == 1
    assert msgs1[0]["body"] == "latest message"

    resp2 = await client.get(
        f"/chats/{chat_id}/messages?limit=1&before_msg_id={msgs1[0]['id']}",
        headers={"X-User-Id": x_user_id},
    )
    assert resp2.status_code == 200
    msgs2 = resp2.json()
    assert len(msgs2) == 1
    assert msgs2[0]["body"] == "first message"


async def test_get_chat_messages_forbidden_for_outsider(client: AsyncClient):
    """An outsider user cannot access chat messages and gets 403."""
    peer_user_id = str(uuid4())
    x_user_id = str(uuid4())
    outsider_id = str(uuid4())

    create_resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": str(peer_user_id)},
        headers={"X-User-Id": str(x_user_id)},
    )
    chat_id = create_resp.json()["id"]

    resp = await client.get(
        f"/chats/{chat_id}/messages?limit=1",
        headers={"X-User-Id": outsider_id},
    )
    assert resp.status_code == 403
