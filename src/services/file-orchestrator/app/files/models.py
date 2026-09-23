"""Models for file-orchestrator service."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.database import Base


class File(Base):
    """A single uploaded file, source of truth for attachment metadata.

    chat_id/uploader_id are plain UUID columns, not foreign keys — they
    reference rows owned by the communication/identity services, which
    have their own databases (same convention as sender_id/created_by
    there).
    """

    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    chat_id: Mapped[UUID] = mapped_column(index=True)
    uploader_id: Mapped[UUID]
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    # Key used to address the blob in SeaweedFS's filer (/attachments/{storage_key}).
    storage_key: Mapped[str] = mapped_column(String(64), unique=True)
    # pending: upload in progress; ready: fully stored, safe to reference in
    # a message; deleted: blob removed from storage, row kept for history.
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
