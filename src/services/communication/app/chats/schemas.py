"""Pydantic schemas for chats."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateDirectChatRequest(BaseModel):
    """Create direct chat request."""

    peer_user_id: UUID


class CreateDirectChatResponse(BaseModel):
    """Create direct chat response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
