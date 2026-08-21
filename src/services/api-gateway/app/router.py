"""Proxy routes for the API gateway."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.dependencies import get_authorization_token

PUBLIC_PATHS = {"auth/register", "auth/login", "auth/refresh"}

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
    if segment in ("auth", "users") or path == "me":
        return settings.identity_url
    if segment == "chats":
        return settings.communication_url
    raise HTTPException(status_code=404)


@router.api_route("/{path:path}", methods=["GET", "POST"], include_in_schema=False)
async def proxy(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """Proxy the request to the target service with the user id attached.

    Args:
        path: URL path without the leading slash.
        request: Incoming client request.
        credentials: Bearer token extracted from the Authorization header.

    Returns:
        Response: Status code, body and content type of the upstream response.

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
    content_type = request.headers.get("content-type")
    if content_type:
        headers["content-type"] = content_type

    async with httpx.AsyncClient() as client:
        upstream = await client.request(
            method=request.method,
            url=f"{target}/{path}",
            params=request.query_params,
            content=await request.body(),
            headers=headers,
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )
