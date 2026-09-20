"""SeaweedFS HTTP client: blob storage (filer) and free-space checks (volume).

Verified empirically against a standalone chrislusf/seaweedfs container:
  PUT/GET/DELETE http://filer:8888/attachments/{key} — raw body, no multipart.
  GET http://volume:8080/status -> {"DiskStatuses": [{"free": <bytes>, ...}]}
"""

from collections.abc import AsyncIterator

import httpx

from app.config import settings


async def get_free_bytes() -> int:
    """Read free disk space (bytes) from the SeaweedFS volume server.

    Returns:
        int: Free bytes on the volume server's data disk.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.seaweedfs_volume_url}/status")
    response.raise_for_status()
    disk_statuses = response.json()["DiskStatuses"]
    return disk_statuses[0]["free"]


async def put_object(
    storage_key: str, content_type: str, body: AsyncIterator[bytes]
) -> None:
    """Stream a blob into the filer under /attachments/{storage_key}.

    Args:
        storage_key: Unique key identifying the blob.
        content_type: MIME type to store alongside the blob.
        body: Async byte chunk iterator for the request body.
    """
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.put(
            f"{settings.seaweedfs_filer_url}/attachments/{storage_key}",
            content=body,
            headers={"Content-Type": content_type},
        )
    response.raise_for_status()


async def delete_object(storage_key: str) -> None:
    """Delete a blob from the filer. No-op (from the caller's perspective) if missing.

    Args:
        storage_key: Unique key identifying the blob to delete.
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.seaweedfs_filer_url}/attachments/{storage_key}"
        )
    if response.status_code not in (204, 404):
        response.raise_for_status()


async def stream_object(storage_key: str) -> tuple[AsyncIterator[bytes], str]:
    """Open a streaming GET for a blob.

    Args:
        storage_key: Unique key identifying the blob to fetch.

    Returns:
        tuple[AsyncIterator[bytes], str]: Byte chunk iterator and content-type.
    """
    client = httpx.AsyncClient(timeout=None)
    request = client.build_request(
        "GET", f"{settings.seaweedfs_filer_url}/attachments/{storage_key}"
    )
    response = await client.send(request, stream=True)
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
