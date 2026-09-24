"""Database configuration and session management module.

This module provides asynchronous database engine and session factory
for SQLAlchemy ORM operations.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Async database engine. echo is off by default: SQLAlchemy logs bound
# parameter values along with each statement, which would otherwise put
# filenames and other file metadata straight into the logs.
engine = create_async_engine(settings.database_url, echo=settings.sql_echo)

# Async session factory.
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for database models."""

    pass
