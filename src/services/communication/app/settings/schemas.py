"""Pydantic schemas for per-chat settings."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatSettingsResponse(BaseModel):
    """Current user's settings for a single chat."""

    model_config = ConfigDict(from_attributes=True)

    chat_id: UUID
    user_id: UUID
    notifications_muted: bool


class ChatSettingsUpdateRequest(BaseModel):
    """Partial update of the current user's settings for a chat."""

    notifications_muted: bool | None = None
