"""Pydantic schemas for chats."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    """Chat list item with its type, title, unread count, and last message."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: Literal["direct", "group"]
    title: str | None = None
    last_message: MessagePreview | None
    unread_count: int = 0


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
    attachment_file_ids: list[UUID] = Field(default_factory=list)


class EditMessageRequest(BaseModel):
    """Request to edit an existing message's text."""

    body: str = Field(min_length=1)


class MarkChatReadRequest(BaseModel):
    """Request to mark a chat read up to (and including) a given message."""

    last_read_message_id: UUID


class MessageResponse(BaseModel):
    """Message Response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    sender_id: UUID
    body: str
    edited_at: datetime | None
    is_deleted: bool
    created_at: datetime
    attachment_file_ids: list[UUID] = Field(default_factory=list)


class CreateGroupChatRequest(BaseModel):
    """Request to create a group chat."""

    title: str = Field(min_length=1, max_length=128)
    member_ids: list[UUID] = Field(default_factory=list)


class CreateGroupChatResponse(BaseModel):
    """Response returned after creating a group chat."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID


class AddGroupMembersRequest(BaseModel):
    """Request to add users to a group chat."""

    user_ids: list[UUID] = Field(min_length=1)


class UpdateGroupChatRequest(BaseModel):
    """Request to update a group chat."""

    title: str = Field(min_length=1, max_length=128)
