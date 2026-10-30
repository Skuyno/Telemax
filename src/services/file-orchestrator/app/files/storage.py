"""SeaweedFS HTTP client: blob storage (filer) and free-space checks (volume).

Verified empirically against a standalone chrislusf/seaweedfs container:
  PUT/GET/DELETE http://filer:8888/attachments/{key} — raw body, no multipart.
  GET http://volume:8080/status -> {"DiskStatuses": [{"free": <bytes>, ...}]}
  GET .../attachments/{key} with a Range header -> 206 + Content-Range, or
    416 + "Content-Range: bytes */<total>" for an out-of-bounds range —
    the filer already implements RFC 7233 range semantics correctly (same
    container), so Range is simply forwarded and the result relayed as-is.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass
class StorageResponse:
    """Result of a GET (optionally for a byte range only) against the blob store."""

    body: AsyncIterator[bytes]
    content_type: str
    status_code: int
    content_length: int | None
    content_range: str | None


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


async def stream_object(
    storage_key: str, range_header: str | None = None
) -> StorageResponse:
    """Open a streaming GET for a blob, optionally for a byte range only.

    A Range header, if given, is forwarded to the filer as-is and its
    response relayed back verbatim (status code, Content-Length and
    Content-Range included) — there's no reason to re-derive byte-range
    arithmetic here when the filer already gets it right.

    Args:
        storage_key: Unique key identifying the blob to fetch.
        range_header: the client's raw Range header value (e.g.
            "bytes=0-1023"), or None for the whole object.

    Returns:
        StorageResponse: byte chunk iterator plus the response's content
            type, status code, content-length and content-range.
    """
    client = httpx.AsyncClient(timeout=None)
    headers = {"Range": range_header} if range_header else {}
    request = client.build_request(
        "GET",
        f"{settings.seaweedfs_filer_url}/attachments/{storage_key}",
        headers=headers,
    )
    response = await client.send(request, stream=True)
    # 416 is an expected, legitimate outcome of an out-of-bounds range, not
    # an error to raise on — anything else 4xx/5xx still is.
    if response.status_code != 416:
        response.raise_for_status()
    content_type = response.headers.get("content-type", "application/octet-stream")
    content_length = response.headers.get("content-length")

    async def _body() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StorageResponse(
        body=_body(),
        content_type=content_type,
        status_code=response.status_code,
        content_length=int(content_length) if content_length is not None else None,
        content_range=response.headers.get("content-range"),
    )
