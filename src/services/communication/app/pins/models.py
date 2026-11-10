"""Models for pinning messages within a chat.

Kept as its own module, independent of `app.chats.models`, same reasoning
as `app.settings` — this domain can evolve on its own without touching the
core chats/messages module.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ChatMessagePin(Base):
    """A message pinned chat-wide — visible to every member of the chat."""

    __tablename__ = "chat_message_pins"

    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id"), primary_key=True)
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id"), primary_key=True
    )
    pinned_by: Mapped[UUID]
    pinned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MessagePinOverride(Base):
    """A single user's override of a message's chat-wide pin state.

    `state="personal_pin"` pins a message just for this user even though
    it isn't pinned chat-wide. `state="hidden"` drops a chat-wide pin from
    just this user's own pinned list without affecting anyone else's. Only
    one override can exist per (user, message) — see app/pins/service.py
    for how the two states combine with ChatMessagePin into one effective
    per-user pin state.
    """

    __tablename__ = "message_pin_overrides"

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id"), primary_key=True
    )
    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id"))
    state: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
