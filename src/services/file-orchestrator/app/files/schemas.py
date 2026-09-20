"""Pydantic schemas for files."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    """A file's metadata, as returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    uploader_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime


class ValidateFilesRequest(BaseModel):
    """Request body for the internal attachment-validation endpoint."""

    chat_id: UUID
    file_ids: list[UUID]


class ValidateFilesResponse(BaseModel):
    """Which of the requested file ids are ready attachments of that chat."""

    valid_file_ids: list[UUID]
