"""Database configuration and session management module.

This module provides asynchronous database engine and session factory
for SQLAlchemy ORM operations.
"""

from config import settings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(settings.database_url, echo=True)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for database models."""

    pass
