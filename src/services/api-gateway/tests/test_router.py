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


def _access_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "type": "access"},
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
                headers={"Authorization": f"Bearer {_access_token(str(uuid4()))}"},
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
                headers={"Authorization": f"Bearer {_access_token(str(uuid4()))}"},
            )

    assert "transfer-encoding" not in resp.headers
    assert "connection" not in resp.headers


async def test_client_cannot_spoof_x_user_id():
    """X-User-Id sent upstream always comes from the verified JWT.

    Never from a client-supplied header, even if the client sends one.
    Raised in code review (PR #22): could a malicious client override
    trust headers like X-User-Id? headers={} is a fresh dict each
    request, X-User-Id is set only from get_authorization_token(), and
    FORWARDED_REQUEST_HEADERS never includes x-user-id or authorization
    — this pins that down with an actual assertion on what's sent.
    """
    real_user_id = str(uuid4())
    attacker_supplied_id = str(uuid4())
    fake_client = _fake_upstream_client(200, {"content-type": "text/plain"}, b"ok")

    with patch("app.router.httpx.AsyncClient", return_value=fake_client):
        transport = ASGITransport(app=app)
        async with HttpClient(transport=transport, base_url="http://test") as client:
            await client.get(
                "/files/some-id",
                headers={
                    "Authorization": f"Bearer {_access_token(real_user_id)}",
                    "X-User-Id": attacker_supplied_id,
                },
            )

    sent_headers = fake_client.build_request.call_args.kwargs["headers"]
    assert sent_headers["X-User-Id"] == real_user_id
    assert "Authorization" not in sent_headers


async def test_content_length_now_passes_through():
    """content-length used to be unconditionally dropped — Range support needs it.

    A <video>/<audio> element can't seek a chunked-transfer response; an
    exact Content-Length (matching the bytes upstream_body() actually
    relays, since it transforms nothing) is what makes that possible.
    """
    fake_client = _fake_upstream_client(
        200, {"content-type": "application/octet-stream", "content-length": "36"}, b"x"
    )
    with patch("app.router.httpx.AsyncClient", return_value=fake_client):
        transport = ASGITransport(app=app)
        async with HttpClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/files/some-id",
                headers={"Authorization": f"Bearer {_access_token(str(uuid4()))}"},
            )

    assert resp.headers["content-length"] == "36"


async def test_range_header_is_forwarded_upstream():
    """A client's Range header reaches file-orchestrator unmodified."""
    fake_client = _fake_upstream_client(
        206,
        {
            "content-type": "application/octet-stream",
            "content-length": "10",
            "content-range": "bytes 0-9/36",
        },
        b"0123456789",
    )
    with patch("app.router.httpx.AsyncClient", return_value=fake_client):
        transport = ASGITransport(app=app)
        async with HttpClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/files/some-id",
                headers={
                    "Authorization": f"Bearer {_access_token(str(uuid4()))}",
                    "Range": "bytes=0-9",
                },
            )

    sent_headers = fake_client.build_request.call_args.kwargs["headers"]
    assert sent_headers["range"] == "bytes=0-9"
    assert resp.status_code == 206
    assert resp.headers["content-range"] == "bytes 0-9/36"


async def _get_with_fake_upstream_status(status: int) -> int:
    fake_client = _fake_upstream_client(
        status, {"content-type": "application/octet-stream"}, b""
    )
    token = _access_token(str(uuid4()))
    with patch("app.router.httpx.AsyncClient", return_value=fake_client):
        transport = ASGITransport(app=app)
        async with HttpClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/files/some-id", headers={"Authorization": f"Bearer {token}"}
            )
    return resp.status_code


async def test_206_and_416_status_codes_pass_through_unchanged():
    """Neither partial-content nor range-not-satisfiable get rewritten to 200."""
    assert await _get_with_fake_upstream_status(206) == 206
    assert await _get_with_fake_upstream_status(416) == 416


async def test_signed_file_link_bypasses_the_bearer_requirement():
    """A GET with sig+exp needs no Authorization header at all.

    This is the whole point of the feature: a <video>/<audio> src can't
    attach one. file-orchestrator does its own signature verification —
    the gateway must not 401 before the request even gets there, and must
    not inject an X-User-Id either (there's no authenticated user here).
    """
    fake_client = _fake_upstream_client(
        200, {"content-type": "application/octet-stream"}, b"video bytes"
    )
    with patch("app.router.httpx.AsyncClient", return_value=fake_client):
        transport = ASGITransport(app=app)
        async with HttpClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/files/some-id?sig=abc123&exp=9999999999")

    assert resp.status_code == 200
    sent_headers = fake_client.build_request.call_args.kwargs["headers"]
    assert "X-User-Id" not in sent_headers


async def test_signed_link_bypass_does_not_apply_to_link_creation():
    """POST .../link still requires a real bearer token, sig/exp or not.

    Only a bare GET on files/{id} is special-cased — creating a link is a
    different path shape (an extra /link segment) and a different method.
    """
    transport = ASGITransport(app=app)
    async with HttpClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/files/some-id/link?sig=abc123&exp=9999999999")

    assert resp.status_code == 401


async def test_signed_link_bypass_does_not_apply_without_both_params():
    """Only sig *and* exp together qualify — either alone still needs a token."""
    transport = ASGITransport(app=app)
    async with HttpClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/files/some-id?sig=abc123")

    assert resp.status_code == 401
