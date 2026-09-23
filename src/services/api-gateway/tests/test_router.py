"""Tests for the proxy route's response header handling.

Mocks the outbound httpx.AsyncClient so these exercise only api-gateway's
own header-forwarding logic, not a real upstream service.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt
from httpx import ASGITransport
from httpx import AsyncClient as HttpClient

from app.config import settings
from app.main import app


def _access_token() -> str:
    return jwt.encode(
        {"sub": str(uuid4()), "type": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _fake_upstream_client(status_code: int, headers: dict, body: bytes) -> MagicMock:
    """A stand-in for httpx.AsyncClient that returns a canned response."""
    fake_response = MagicMock()
    fake_response.status_code = status_code
    fake_response.headers = headers

    async def _aiter_bytes():
        yield body

    fake_response.aiter_bytes = _aiter_bytes
    fake_response.aclose = AsyncMock()

    fake_client = MagicMock()
    fake_client.build_request = MagicMock(return_value=object())
    fake_client.send = AsyncMock(return_value=fake_response)
    fake_client.aclose = AsyncMock()
    return fake_client


async def test_content_disposition_survives_the_proxy():
    """A download's Content-Disposition (original filename) reaches the client."""
    fake_client = _fake_upstream_client(
        200,
        {
            "content-type": "text/plain",
            "content-disposition": 'attachment; filename="report.txt"',
            "content-length": "5",
        },
        b"hello",
    )
    with patch("app.router.httpx.AsyncClient", return_value=fake_client):
        transport = ASGITransport(app=app)
        async with HttpClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/files/some-id",
                headers={"Authorization": f"Bearer {_access_token()}"},
            )

    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == 'attachment; filename="report.txt"'
    assert resp.content == b"hello"


async def test_hop_by_hop_response_headers_are_dropped():
    """Headers StreamingResponse recomputes itself aren't blindly replayed."""
    fake_client = _fake_upstream_client(
        200,
        {
            "content-type": "text/plain",
            "transfer-encoding": "chunked",
            "connection": "keep-alive",
            "content-length": "1",
        },
        b"x",
    )
    with patch("app.router.httpx.AsyncClient", return_value=fake_client):
        transport = ASGITransport(app=app)
        async with HttpClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/files/some-id",
                headers={"Authorization": f"Bearer {_access_token()}"},
            )

    assert "transfer-encoding" not in resp.headers
    assert "connection" not in resp.headers
