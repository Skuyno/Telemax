"""Tests for the user directory search endpoint."""

from httpx import AsyncClient

from app.users.models import User
from app.users.security import hash_password


async def _create_user(db_session_maker, **fields) -> None:
    async with db_session_maker() as session:
        session.add(User(password_hash=hash_password("irrelevant"), **fields))
        await session.commit()


async def test_search_by_tag_prefix_case_insensitive(
    client: AsyncClient, db_session_maker
):
    """Tag search matches a case-insensitive prefix of the username."""
    await _create_user(db_session_maker, username="Alice")
    await _create_user(db_session_maker, username="alicia")
    await _create_user(db_session_maker, username="bob")

    resp = await client.post("/users/search", json={"tag": "ali", "limit": 30})
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.json()}
    assert usernames == {"Alice", "alicia"}


async def test_search_by_tag_strips_leading_at(client: AsyncClient, db_session_maker):
    """A leading "@" on the tag filter is ignored."""
    await _create_user(db_session_maker, username="alice")

    resp = await client.post("/users/search", json={"tag": "@ali", "limit": 30})
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alice"]


async def test_search_tag_does_not_match_mid_string(
    client: AsyncClient, db_session_maker
):
    """Tag search only matches a leading prefix, not an arbitrary substring."""
    await _create_user(db_session_maker, username="alice")

    resp = await client.post("/users/search", json={"tag": "lic", "limit": 30})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_by_email_substring_case_insensitive(
    client: AsyncClient, db_session_maker
):
    """Email search matches any case-insensitive substring."""
    await _create_user(db_session_maker, username="alice", email="alice@example.com")
    await _create_user(db_session_maker, username="bob", email="bob@other.com")

    resp = await client.post("/users/search", json={"email": "EXAMPLE", "limit": 30})
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alice"]


async def test_search_by_phone_substring(client: AsyncClient, db_session_maker):
    """Phone search matches any substring."""
    await _create_user(db_session_maker, username="alice", phone="+79991234567")
    await _create_user(db_session_maker, username="bob", phone="+15550001111")

    resp = await client.post("/users/search", json={"phone": "9991234", "limit": 30})
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alice"]


async def test_search_by_name_substring(client: AsyncClient, db_session_maker):
    """Display-name search matches any case-insensitive substring."""
    await _create_user(db_session_maker, username="alice", display_name="Al Pacino")
    await _create_user(db_session_maker, username="bob", display_name="Bob Dylan")

    resp = await client.post("/users/search", json={"name": "pacino", "limit": 30})
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alice"]


async def test_search_query_matches_email_phone_or_name_but_not_tag(
    client: AsyncClient, db_session_maker
):
    """The `query` shortcut searches email/phone/name, never the tag/username."""
    await _create_user(db_session_maker, username="alice", display_name="Al Pacino")
    await _create_user(db_session_maker, username="pacino_fan")

    resp = await client.post("/users/search", json={"query": "pacino", "limit": 30})
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alice"]


async def test_search_combining_filters_is_and(client: AsyncClient, db_session_maker):
    """Giving multiple fields at once narrows results (logical AND)."""
    await _create_user(db_session_maker, username="alice", display_name="Al Pacino")
    await _create_user(db_session_maker, username="alina", display_name="Alina Bob")

    resp = await client.post(
        "/users/search", json={"tag": "ali", "name": "pacino", "limit": 30}
    )
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["alice"]


async def test_search_requires_at_least_one_filter(client: AsyncClient):
    """A search body with no filter fields at all is rejected."""
    resp = await client.post("/users/search", json={"limit": 30})
    assert resp.status_code == 422


async def test_search_requires_limit(client: AsyncClient):
    """`limit` has no default and must be supplied explicitly."""
    resp = await client.post("/users/search", json={"tag": "a"})
    assert resp.status_code == 422


async def test_search_respects_limit_and_orders_by_username(
    client: AsyncClient, db_session_maker
):
    """No more than `limit` results are returned, ordered by username."""
    for name in ["a4", "a2", "a1", "a3"]:
        await _create_user(db_session_maker, username=name)

    resp = await client.post("/users/search", json={"tag": "a", "limit": 2})
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert usernames == ["a1", "a2"]


async def test_search_response_excludes_password_and_includes_id(
    client: AsyncClient, db_session_maker
):
    """Search results never leak the password hash, but do include id."""
    await _create_user(db_session_maker, username="alice")

    resp = await client.post("/users/search", json={"tag": "alice", "limit": 30})
    body = resp.json()[0]
    assert "password_hash" not in body
    assert "password" not in body
    assert "id" in body
