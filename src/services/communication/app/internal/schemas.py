"""Schemas for internal service endpoints."""

from uuid import UUID

from pydantic import BaseModel


class ChatPeersResponse(BaseModel):
    """Response containing IDs of users who share a chat with a user."""

    user_ids: list[UUID]
