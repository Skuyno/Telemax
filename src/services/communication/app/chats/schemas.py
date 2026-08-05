"""Pydantic schemas for chats."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateDirectChatRequest(BaseModel):
    """Create direct chat request."""

    peer_user_id: UUID


class CreateDirectChatResponse(BaseModel):
    """Create direct chat response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID


class MessagePreview(BaseModel):
    """Preview of a chat's most recent message."""

    model_config = ConfigDict(from_attributes=True)

    body: str
    sender_id: UUID
    created_at: datetime


class ChatResponse(BaseModel):
    """Chat list item: id and a preview of the last message."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    last_message: MessagePreview | None


class ChatMembersResponse(BaseModel):
    """somtehing."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    role: str
    joined_at: datetime


class SendMessageRequest(BaseModel):
    """Message request."""

    body: str
    client_msg_id: UUID


class MessageResponse(BaseModel):
    """Message Response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    sender_id: UUID
    created_at: datetime

