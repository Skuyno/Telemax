"""Database configuration and session management module.

This module provides asynchronous database engine and session factory
for SQLAlchemy ORM operations.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Async database engine.
engine = create_async_engine(settings.database_url, echo=True)

# Async session factory.
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for database models."""

    pass
