"""SeaweedFS HTTP client for group chat avatars.

Same filer HTTP API, same fixed-key-per-owner convention as identity's
`app/users/storage.py` for user avatars (raw PUT/GET/DELETE, no
multipart) — just keyed by chat id instead of user id.
"""

from collections.abc import AsyncIterator

import httpx

from app.config import settings


def _avatar_path(chat_id: str) -> str:
    """Path (within the filer) for a chat's avatar blob."""
    return f"/chat-avatars/{chat_id}"


async def put_avatar(
    chat_id: str, content_type: str, body: AsyncIterator[bytes]
) -> None:
    """Stream an avatar image into the filer, replacing any existing one.

    Args:
        chat_id: The group chat the avatar belongs to.
        content_type: MIME type to store alongside the blob.
        body: Async byte chunk iterator for the request body.
    """
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.put(
            f"{settings.seaweedfs_filer_url}{_avatar_path(chat_id)}",
            content=body,
            headers={"Content-Type": content_type},
        )
    response.raise_for_status()


async def delete_avatar(chat_id: str) -> None:
    """Delete a chat's avatar blob. No-op if there isn't one.

    Args:
        chat_id: The group chat whose avatar to delete.
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.seaweedfs_filer_url}{_avatar_path(chat_id)}"
        )
    if response.status_code not in (204, 404):
        response.raise_for_status()


async def stream_avatar(chat_id: str) -> tuple[AsyncIterator[bytes], str] | None:
    """Open a streaming GET for a chat's avatar.

    Args:
        chat_id: The group chat whose avatar to fetch.

    Returns:
        tuple[AsyncIterator[bytes], str] | None: Byte chunk iterator and
        content-type, or None if the chat has no avatar stored.
    """
    client = httpx.AsyncClient(timeout=None)
    request = client.build_request(
        "GET", f"{settings.seaweedfs_filer_url}{_avatar_path(chat_id)}"
    )
    response = await client.send(request, stream=True)
    if response.status_code == 404:
        await response.aclose()
        await client.aclose()
        return None
    response.raise_for_status()
    content_type = response.headers.get("content-type", "application/octet-stream")

    async def _body() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return _body(), content_type
