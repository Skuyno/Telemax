from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Создание асинхронного движка б.д.
engine = create_async_engine(settings.database_url, echo=True)

# Генератор асинхронных сессий б.д.
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для моделей б.д."""
    pass
