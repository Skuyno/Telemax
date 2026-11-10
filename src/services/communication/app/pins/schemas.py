"""Pydantic schemas for message pins."""

from typing import Literal

from pydantic import BaseModel

from app.chats.schemas import MessageResponse


class PinMessageRequest(BaseModel):
    """Request to pin a message, either for the caller only or for everyone."""

    scope: Literal["me", "everyone"]


class UnpinMessageRequest(BaseModel):
    """Request to unpin a message, either for the caller only or for everyone."""

    scope: Literal["me", "everyone"]


class PinnedMessageResponse(MessageResponse):
    """A pinned message, with the scope it's pinned at for the caller."""

    pin_scope: Literal["me", "everyone"]
