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


class NotificationsChatResponse(BaseModel):
    """A user's personal "Уведомления" chat id."""

    chat_id: UUID


class BroadcastRequest(BaseModel):
    """Request to send a system message into every target user's own chat."""

    sender_id: UUID
    body: str
    attachment_file_ids: list[UUID] = []
    # None = everyone; a specific list is the hook for a future
    # targeted-at-specific-users broadcast — not exposed in the UI yet.
    user_ids: list[UUID] | None = None


class BroadcastResponse(BaseModel):
    """How many users a broadcast was actually sent to."""

    recipient_count: int


class FileAccessResponse(BaseModel):
    """Whether a user can access a file via some message they can see.

    Used by file-orchestrator to authorize downloads/signed links: "can you
    see a message that attaches this file", not "were you a member of the
    chat it was originally uploaded into" — the distinction matters for a
    broadcast attachment, which lives in one chat but is attached to a
    message in every recipient's own separate chat.
    """

    authorized: bool
