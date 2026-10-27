"""Public routes for uploading, downloading and deleting files."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, get_current_user_id
from app.files import service as files_service
from app.files.schemas import FileLinkResponse, FileResponse

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
    range_header: str | None = Header(default=None, alias="Range"),
    x_user_id: UUID | None = Header(default=None),
    sig: str | None = None,
    exp: int | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> StreamingResponse:
    """Stream a file's bytes — the whole file or a single byte range.

    Authorization is via the usual X-User-Id (chat membership check), or,
    for places a browser can't attach an Authorization header (a <video>/
    <audio> src), a short-lived signed link's sig+exp query params instead
    — see create_file_link below.

    Args:
        file_id: Id of the file to download.
        range_header: The client's Range header, if any (e.g. "bytes=0-1023").
        x_user_id: User id trusted from the X-User-Id header, if present.
        sig: Signed-link signature, if accessing via a signed link.
        exp: Signed-link expiry (unix timestamp), if accessing via a signed link.
        db: Async database session.

    Returns:
        StreamingResponse: 200 (whole file), 206 (byte range), or 416
        (range not satisfiable), with Accept-Ranges/Content-Length/
        Content-Range set accordingly.
    """
    file, content = await files_service.download_file(
        db, file_id, user_id=x_user_id, sig=sig, exp=exp, range_header=range_header
    )
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'attachment; filename="{file.original_filename}"',
    }
    if content.content_length is not None:
        headers["Content-Length"] = str(content.content_length)
    if content.content_range is not None:
        headers["Content-Range"] = content.content_range
    return StreamingResponse(
        content.body,
        status_code=content.status_code,
        media_type=file.content_type,
        headers=headers,
    )


@router.post("/{file_id}/link", tags=["Files"])
async def create_file_link(
    file_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
) -> FileLinkResponse:
    """Issue a short-lived signed link, usable with no Authorization header.

    Meant for <video>/<audio> src attributes, which can't send a bearer
    token — requesting this link requires the same authorization as a
    normal download (chat membership); the signature alone authorizes the
    actual download afterward.

    Args:
        file_id: Id of the file to issue a link for.
        user_id: User id trusted from the X-User-Id header.
        db: Async database session.

    Returns:
        FileLinkResponse: A relative download URL (sig+exp query params)
        and how many seconds it's valid for.
    """
    url, expires_in = await files_service.create_file_link(db, file_id, user_id)
    return FileLinkResponse(url=url, expires_in=expires_in)
