"""Business logic for uploading, downloading and deleting files."""

import logging
from collections.abc import AsyncIterator
from dataclasses import replace
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.config import settings
from app.events import nats_client
from app.files import links, storage
from app.files import repository as files_repository
from app.files.models import File
from app.files.storage import StorageResponse

logger = logging.getLogger(__name__)


async def assert_chat_member(chat_id: UUID, user_id: UUID) -> None:
    """Verify the user is a member of the chat, via communication's internal API.

    Raises:
        HTTPException: 403 if the user isn't a member of the chat.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.communication_url}/internal/chats/{chat_id}/members/{user_id}"
        )
    response.raise_for_status()
    if not response.json()["is_member"]:
        raise HTTPException(status_code=403, detail="not a member of this chat")


async def _get_chat_member_ids(chat_id: UUID) -> list[str]:
    """Fetch every member's user id, so ws-gateway knows who to notify."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.communication_url}/internal/chats/{chat_id}/members"
        )
    response.raise_for_status()
    return response.json()["user_ids"]


async def upload_file(
    db: AsyncSession,
    chat_id: UUID,
    uploader_id: UUID,
    original_filename: str,
    content_type: str,
    declared_size: int | None,
    body: AsyncIterator[bytes],
) -> File:
    """Stream an upload into storage, enforcing size limits and reporting progress.

    Two size guards apply, both checked against the actual bytes received (not
    just the declared Content-Length, which a client could misreport):
      - the admin-configurable policy limit (settings.max_upload_size_bytes,
        None = unlimited);
      - the SeaweedFS volume's free disk space, always enforced regardless of
        the policy limit.

    Raises:
        HTTPException: 413 if the upload exceeds either limit.
    """
    await assert_chat_member(chat_id, uploader_id)

    free_bytes = await storage.get_free_bytes()
    policy_limit = settings.max_upload_size_bytes
    effective_limit = (
        free_bytes if policy_limit is None else min(policy_limit, free_bytes)
    )

    if declared_size is not None and declared_size > effective_limit:
        raise HTTPException(status_code=413, detail="file exceeds allowed size")

    file_id = uuid7()
    file = await files_repository.create_pending_file(
        db, file_id, chat_id, uploader_id, original_filename, content_type
    )
    recipient_ids = await _get_chat_member_ids(chat_id)

    bytes_received = 0
    bytes_since_last_progress = 0

    async def _counted_body() -> AsyncIterator[bytes]:
        nonlocal bytes_received, bytes_since_last_progress
        async for chunk in body:
            bytes_received += len(chunk)
            if bytes_received > effective_limit:
                raise HTTPException(status_code=413, detail="file exceeds allowed size")

            bytes_since_last_progress += len(chunk)
            if bytes_since_last_progress >= settings.upload_progress_interval_bytes:
                bytes_since_last_progress = 0
                await nats_client.publish(
                    "file.upload.progress",
                    {
                        "file_id": str(file_id),
                        "chat_id": str(chat_id),
                        "uploader_id": str(uploader_id),
                        "bytes_uploaded": bytes_received,
                        "size_bytes": declared_size,
                        "recipient_ids": recipient_ids,
                    },
                )
            yield chunk

    try:
        await storage.put_object(file.storage_key, content_type, _counted_body())
    except HTTPException:
        await files_repository.mark_deleted(db, file_id)
        raise

    await files_repository.mark_ready(db, file_id, bytes_received)
    await nats_client.publish(
        "file.upload.completed",
        {
            "file_id": str(file_id),
            "chat_id": str(chat_id),
            "uploader_id": str(uploader_id),
            "size_bytes": bytes_received,
            "recipient_ids": recipient_ids,
        },
    )
    return await files_repository.get_file(db, file_id)


async def download_file(
    db: AsyncSession,
    file_id: UUID,
    user_id: UUID | None,
    sig: str | None,
    exp: int | None,
    range_header: str | None,
) -> tuple[File, StorageResponse]:
    """Authorize (via chat membership or a signed link) and fetch a file's bytes.

    A signed link (sig + exp) is a self-contained credential, checked first
    and independently of any X-User-Id also present — it's the one path a
    browser can use with no Authorization header at all (see
    app/files/links.py and create_file_link below).

    Raises:
        HTTPException: 404 if the file doesn't exist or isn't ready, 401 if
            neither a user id nor a signed link was given, 403 if the
            signed link is invalid/expired or the user isn't a chat member.
    """
    file = await files_repository.get_file(db, file_id)
    if file is None or file.status != "ready":
        raise HTTPException(status_code=404, detail="file not found")

    if sig is not None and exp is not None:
        if not links.verify_link(str(file_id), sig, exp):
            raise HTTPException(status_code=403, detail="invalid or expired link")
    elif user_id is not None:
        await assert_chat_member(file.chat_id, user_id)
    else:
        raise HTTPException(status_code=401, detail="authorization required")

    storage_response = await storage.stream_object(file.storage_key, range_header)
    if range_header is None:
        # Already known from our own record — no need to trust/recompute
        # from the storage response for the whole-file case.
        storage_response = replace(
            storage_response,
            status_code=200,
            content_length=file.size_bytes,
            content_range=None,
        )
    return file, storage_response


async def create_file_link(
    db: AsyncSession, file_id: UUID, user_id: UUID
) -> tuple[str, int]:
    """Authorize and issue a signed, short-lived download link.

    Raises:
        HTTPException: 404 if the file doesn't exist or isn't ready, 403 if
            the caller isn't a member of the file's chat.
    """
    file = await files_repository.get_file(db, file_id)
    if file is None or file.status != "ready":
        raise HTTPException(status_code=404, detail="file not found")

    await assert_chat_member(file.chat_id, user_id)

    sig, exp = links.issue_link(str(file_id))
    url = f"/files/{file_id}?sig={sig}&exp={exp}"
    return url, links.LINK_TTL_SECONDS


async def delete_file(db: AsyncSession, file_id: UUID) -> None:
    """Delete a file's blob and mark it deleted. Idempotent."""
    file = await files_repository.get_file(db, file_id)
    if file is None or file.status == "deleted":
        return
    await storage.delete_object(file.storage_key)
    await files_repository.mark_deleted(db, file_id)


async def validate_files(
    db: AsyncSession, chat_id: UUID, file_ids: list[UUID]
) -> list[UUID]:
    """Return the subset of file_ids that are ready attachments of chat_id."""
    files = await files_repository.get_ready_files_in_chat(db, chat_id, file_ids)
    return [f.id for f in files]
