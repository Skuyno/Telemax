"""Schemas for internal service endpoints."""

from uuid import UUID

from pydantic import BaseModel


class ChatPeersResponse(BaseModel):
    """Response containing IDs of users who share a chat with a user."""

    user_ids: list[UUID]


class ChatMembershipResponse(BaseModel):
    """Whether a user is a member of a chat."""

    is_member: bool


class ChatMemberIdsResponse(BaseModel):
    """IDs of all members of a chat."""

    user_ids: list[UUID]
