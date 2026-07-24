"""Tests for the chat endpoints."""

from uuid import UUID, uuid4

from conftest import test_session_maker as session_maker
from httpx import AsyncClient

from app.chats.models import Message


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

    async with session_maker() as session:
        session.add(Message(chat_id=chat_id, sender_id=x_user_id, body="first message"))
        session.add(
            Message(chat_id=chat_id, sender_id=peer_user_id, body="latest message")
        )
        await session.commit()

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

    async with session_maker() as session:
        session.add(
            Message(chat_id=first_chat_id, sender_id=x_user_id, body="from first chat")
        )
        session.add(
            Message(
                chat_id=second_chat_id, sender_id=x_user_id, body="from second chat"
            )
        )
        await session.commit()

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
