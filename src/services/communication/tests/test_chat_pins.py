"""Tests for pinning chats (a personal, per-user setting)."""

from uuid import uuid4

from httpx import AsyncClient


async def _create_chat(client: AsyncClient, creator_id: str, peer_id: str) -> str:
    resp = await client.post(
        "/chats/direct",
        json={"peer_user_id": peer_id},
        headers={"X-User-Id": creator_id},
    )
    return resp.json()["id"]


async def test_pinning_a_chat_marks_it_pinned_in_settings_and_chat_list(
    client: AsyncClient,
):
    """Pinning via the settings endpoint is reflected in both responses."""
    user_id = str(uuid4())
    chat_id = await _create_chat(client, user_id, str(uuid4()))

    resp = await client.patch(
        f"/chats/{chat_id}/settings",
        json={"is_pinned": True},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 200
    assert resp.json()["is_pinned"] is True

    chats = await client.get("/chats", headers={"X-User-Id": user_id})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["is_pinned"] is True


async def test_unpinning_a_chat_clears_the_flag(client: AsyncClient):
    """Setting is_pinned back to false unpins the chat."""
    user_id = str(uuid4())
    chat_id = await _create_chat(client, user_id, str(uuid4()))

    await client.patch(
        f"/chats/{chat_id}/settings",
        json={"is_pinned": True},
        headers={"X-User-Id": user_id},
    )
    resp = await client.patch(
        f"/chats/{chat_id}/settings",
        json={"is_pinned": False},
        headers={"X-User-Id": user_id},
    )
    assert resp.json()["is_pinned"] is False

    chats = await client.get("/chats", headers={"X-User-Id": user_id})
    chat = next(c for c in chats.json() if c["id"] == chat_id)
    assert chat["is_pinned"] is False


async def test_pinning_is_personal_to_the_pinning_user(client: AsyncClient):
    """One member pinning a shared chat doesn't pin it for the other."""
    user_a = str(uuid4())
    user_b = str(uuid4())
    chat_id = await _create_chat(client, user_a, user_b)

    await client.patch(
        f"/chats/{chat_id}/settings",
        json={"is_pinned": True},
        headers={"X-User-Id": user_a},
    )

    chats_b = await client.get("/chats", headers={"X-User-Id": user_b})
    chat_for_b = next(c for c in chats_b.json() if c["id"] == chat_id)
    assert chat_for_b["is_pinned"] is False


async def test_pinned_chat_sorts_above_unpinned_chats(client: AsyncClient):
    """A pinned chat floats to the top of the chat list regardless of order."""
    user_id = str(uuid4())
    first_chat_id = await _create_chat(client, user_id, str(uuid4()))
    second_chat_id = await _create_chat(client, user_id, str(uuid4()))

    await client.patch(
        f"/chats/{second_chat_id}/settings",
        json={"is_pinned": True},
        headers={"X-User-Id": user_id},
    )

    chats = await client.get("/chats", headers={"X-User-Id": user_id})
    chat_ids = [c["id"] for c in chats.json()]
    assert chat_ids.index(second_chat_id) < chat_ids.index(first_chat_id)


async def test_most_recently_pinned_chat_sorts_first(client: AsyncClient):
    """Among several pinned chats, the most recently pinned one comes first."""
    user_id = str(uuid4())
    older_pin_id = await _create_chat(client, user_id, str(uuid4()))
    newer_pin_id = await _create_chat(client, user_id, str(uuid4()))

    await client.patch(
        f"/chats/{older_pin_id}/settings",
        json={"is_pinned": True},
        headers={"X-User-Id": user_id},
    )
    await client.patch(
        f"/chats/{newer_pin_id}/settings",
        json={"is_pinned": True},
        headers={"X-User-Id": user_id},
    )

    chats = await client.get("/chats", headers={"X-User-Id": user_id})
    chat_ids = [c["id"] for c in chats.json()]
    assert chat_ids.index(newer_pin_id) < chat_ids.index(older_pin_id)


async def test_settings_forbidden_for_outsider(client: AsyncClient):
    """Someone outside the chat cannot read or change its settings."""
    user_id = str(uuid4())
    chat_id = await _create_chat(client, user_id, str(uuid4()))
    outsider = str(uuid4())

    resp = await client.patch(
        f"/chats/{chat_id}/settings",
        json={"is_pinned": True},
        headers={"X-User-Id": outsider},
    )
    assert resp.status_code == 403
