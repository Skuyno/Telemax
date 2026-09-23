"""Models for per-chat user settings in the communication service.

Kept as its own table, independent of `app.chats.models.ChatMember`, so the
chats domain stays focused on chats/messages and settings can evolve on its
own without touching that module.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ChatSettings(Base):
    """Per-user settings for a single chat, e.g. notification muting."""

    __tablename__ = "chat_settings"

    chat_id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    notifications_muted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
