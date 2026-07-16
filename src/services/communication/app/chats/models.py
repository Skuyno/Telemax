"""Models for communication service."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.database import Base


class Chat(Base):
    """Chat model representing a chat in a communication service."""

    __tablename__ = "chats"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    type: Mapped[str] = mapped_column(String(16), default="direct")
    created_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChatMember(Base):
    """Chat model representing a chat member in a communication service."""

    __tablename__ = "chat_members"

    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(16), default="member")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Message(Base):
    """Chat model representing a message in a communication service."""

    __tablename__ = "messages"

    __table_args__ = (
        Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),
        UniqueConstraint("sender_id", "client_msg_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id"))
    sender_id: Mapped[UUID]
    body: Mapped[str] = mapped_column(Text)
    client_msg_id: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DirectChat(Base):
    """Direct-chat subtype data: one chat per user pair (user_lo < user_hi)."""

    __tablename__ = "direct_chats"
    __table_args__ = (
        (CheckConstraint("user_lo <= user_hi", name="ck_direct_chats_pair_ordered")),
    )

    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id"), unique=True)
    user_lo: Mapped[UUID] = mapped_column(primary_key=True)
    user_hi: Mapped[UUID] = mapped_column(primary_key=True)
