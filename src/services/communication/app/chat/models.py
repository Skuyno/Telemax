"""Models for communication service."""

from uuid import UUID

from database import Base

from sqlalchemy.orm import Mapped


class Chat(Base):
    """..."""

    id: Mapped[UUID]
