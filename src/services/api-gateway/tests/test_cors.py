"""Tests for cross-origin exposure of headers a file download needs.

Content-Disposition (filename) and Content-Range (size, via a one-byte
Range request on a signed link) aren't in the CORS-safelisted response
header set — without an explicit Access-Control-Expose-Headers, a
cross-origin caller (npm run dev, or NUXT_PUBLIC_API_BASE pointed straight
at the gateway) can't read either from JS, even though the browser receives
them fine. A same-origin deploy (nginx) never hits this, since CORS doesn't
apply there at all.
"""

from httpx import ASGITransport
from httpx import AsyncClient as HttpClient

from app.main import app


async def test_file_headers_are_exposed_cross_origin():
    """A cross-origin request can read Content-Disposition/Content-Range from JS."""
    transport = ASGITransport(app=app)
    async with HttpClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/files/some-id", headers={"Origin": "http://localhost:3000"}
        )

    exposed = resp.headers["access-control-expose-headers"]
    assert "Content-Disposition" in exposed
    assert "Content-Range" in exposed
