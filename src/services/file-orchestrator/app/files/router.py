"""Public routes for uploading, downloading and deleting files."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, get_current_user_id
from app.files import service as files_service
from app.files.schemas import FileResponse

router = APIRouter(prefix="/files")


@router.post("", status_code=201, tags=["Files"])
async def upload_file(
    chat_id: UUID,
    request: Request,
    x_filename: str = Header(...),
    content_type: str = Header("application/octet-stream"),
    content_length: int | None = Header(default=None),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> FileResponse:
    """Upload a file as a raw streamed request body (no multipart).

    Metadata travels in headers/query since the body is pure file bytes,
    matching the streaming proxy in api-gateway which forwards the request
    body as-is without buffering it.

    Args:
        chat_id: Chat this file is being attached to.
        request: Used to stream the raw request body.
        x_filename: Original filename, since the body carries no metadata.
        content_type: MIME type of the file.
        content_length: Declared size, used only as an early size hint.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        FileResponse: The stored file's metadata.
    """
    file = await files_service.upload_file(
        db,
        chat_id,
        user_id,
        x_filename,
        content_type,
        content_length,
        request.stream(),
    )
    return FileResponse.model_validate(file)


@router.get("/{file_id}", tags=["Files"])
async def download_file(
    file_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> StreamingResponse:
    """Stream a file's bytes back to an authorized caller.

    Args:
        file_id: Id of the file to download.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        StreamingResponse: The file's bytes, streamed from storage.
    """
    file, body = await files_service.download_file(db, file_id, user_id)
    return StreamingResponse(
        body,
        media_type=file.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file.original_filename}"'
        },
    )
