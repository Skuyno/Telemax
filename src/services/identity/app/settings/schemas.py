"""Pydantic schemas for user settings."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserSettingsResponse(BaseModel):
    """Current user's settings response."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    notifications_enabled: bool
    accept_calls: bool


class UserSettingsUpdateRequest(BaseModel):
    """Partial update of the current user's settings."""

    notifications_enabled: bool | None = None
    accept_calls: bool | None = None
