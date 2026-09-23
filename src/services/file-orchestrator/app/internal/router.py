"""Internal (service-to-service) routes, bypassing the X-User-Id trust model."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db
from app.files import service as files_service
from app.files.schemas import ValidateFilesRequest, ValidateFilesResponse

router = APIRouter(prefix="/internal")


@router.post("/files/validate")
async def validate_files(
    data: ValidateFilesRequest,
    db: AsyncSession = Depends(get_async_db),
) -> ValidateFilesResponse:
    """Check which of a set of file ids are ready attachments of a chat.

    Called by communication when a message is sent with attachment_file_ids.

    Args:
        data: Chat id and the file ids to check.
        db: Async database session.

    Returns:
        ValidateFilesResponse: The subset of file ids that are valid.
    """
    valid_ids = await files_service.validate_files(db, data.chat_id, data.file_ids)
    return ValidateFilesResponse(valid_file_ids=valid_ids)
