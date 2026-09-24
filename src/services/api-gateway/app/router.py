"""Proxy routes for the API gateway."""

from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.dependencies import get_authorization_token

PUBLIC_PATHS = {"auth/register", "auth/login", "auth/refresh"}

# Forwarded as-is when present; everything else (Authorization included) is
# replaced by our own X-User-Id, not passed through to upstream services.
# x-filename carries the original filename for raw (non-multipart) file
# uploads to file-orchestrator, which has no other way to receive it.
FORWARDED_REQUEST_HEADERS = ("content-type", "content-length", "x-filename")

# Hop-by-hop headers plus ones StreamingResponse computes itself (it sends
# the body chunked, so upstream's original content-length/content-encoding
# would be wrong) or that don't make sense to replay a second time. Every
# other upstream response header (notably Content-Disposition, needed for
# file-orchestrator downloads to carry the original filename) passes through.
DROPPED_RESPONSE_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "content-encoding",
}

router = APIRouter()

bearer_scheme = HTTPBearer(auto_error=False)


def resolve_target(path: str) -> str:
    """Resolve the upstream service base URL for a request path.

    Args:
        path: URL path without the leading slash.

    Returns:
        str: Base URL of the target service.

    Raises:
        HTTPException: 404 if the path doesn't belong to any service.
    """
    segment = path.split("/", 1)[0]
    if segment in ("auth", "users", "me", "admin"):
        return settings.identity_url
    if segment == "chats":
        return settings.communication_url
    if segment == "files":
        return settings.file_orchestrator_url
    raise HTTPException(status_code=404)


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def proxy(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """Stream the request to the target service and stream its response back.

    Neither direction buffers the full body in memory — required for large
    file uploads/downloads through `files/...`, and free for everything
    else. The request/response bodies are read from and written to the
    network in chunks as they arrive.

    Args:
        path: URL path without the leading slash.
        request: Incoming client request.
        credentials: Bearer token extracted from the Authorization header.

    Returns:
        StreamingResponse: Status code, headers, and streamed body from the
        upstream service.

    Raises:
        HTTPException: 401 if the path is protected and the token is missing
            or invalid, 404 if the path doesn't belong to any service.
    """
    path = path.rstrip("/")
    target = resolve_target(path)

    headers = {}
    if path not in PUBLIC_PATHS:
        user_id = get_authorization_token(credentials)
        headers["X-User-Id"] = str(user_id)
    for header_name in FORWARDED_REQUEST_HEADERS:
        value = request.headers.get(header_name)
        if value:
            headers[header_name] = value

    client = httpx.AsyncClient()
    upstream_request = client.build_request(
        method=request.method,
        url=f"{target}/{path}",
        # Starlette's QueryParams.items() collapses repeated keys to the
        # last value (plain Mapping semantics), and httpx treats a
        # Mapping the same way. multi_items() keeps every pair, so
        # "?ids=a&ids=b" is actually forwarded as both, not just "b".
        params=request.query_params.multi_items(),
        content=request.stream(),
        headers=headers,
    )
    upstream = await client.send(upstream_request, stream=True)

    async def upstream_body() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in DROPPED_RESPONSE_HEADERS
    }

    return StreamingResponse(
        upstream_body(),
        status_code=upstream.status_code,
        headers=response_headers,
    )
