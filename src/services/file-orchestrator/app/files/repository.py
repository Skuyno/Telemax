"""Database access for files."""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.files.models import File


async def create_pending_file(
    db: AsyncSession,
    file_id: UUID,
    chat_id: UUID,
    uploader_id: UUID,
    original_filename: str,
    content_type: str,
) -> File:
    """Insert a new file row in "pending" status, before any bytes are stored."""
    file = File(
        id=file_id,
        chat_id=chat_id,
        uploader_id=uploader_id,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=0,
        storage_key=str(file_id),
        status="pending",
    )
    db.add(file)
    await db.commit()
    await db.refresh(file)
    return file


async def mark_ready(db: AsyncSession, file_id: UUID, size_bytes: int) -> None:
    """Mark a file as fully stored, recording its final size."""
    file = await get_file(db, file_id)
    if file is None:
        return
    file.status = "ready"
    file.size_bytes = size_bytes
    await db.commit()


async def mark_deleted(db: AsyncSession, file_id: UUID) -> None:
    """Mark a file as deleted (blob removed from storage)."""
    file = await get_file(db, file_id)
    if file is None:
        return
    file.status = "deleted"
    file.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def get_file(db: AsyncSession, file_id: UUID) -> File | None:
    """Fetch a single file row by id."""
    result = await db.execute(select(File).where(File.id == file_id))
    return result.scalar_one_or_none()


async def get_ready_files_in_chat(
    db: AsyncSession, chat_id: UUID, file_ids: Sequence[UUID]
) -> list[File]:
    """Fetch the subset of file_ids that are ready attachments of chat_id."""
    result = await db.execute(
        select(File).where(
            File.chat_id == chat_id,
            File.id.in_(file_ids),
            File.status == "ready",
        )
    )
    return list(result.scalars().all())
