"""Service entry point."""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI

from app.config import settings
from app.database import async_session_maker
from app.events import nats_client
from app.files.router import router as files_router
from app.files.service import delete_file
from app.health.router import router as health_router
from app.internal.router import router as internal_router


async def _on_message_deleted(data: dict) -> None:
    """Garbage-collect attachment blobs when their message is deleted."""
    async with async_session_maker() as db:
        for file_id in data.get("attachment_file_ids", []):
            await delete_file(db, UUID(file_id))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan resources like the NATS connection."""
    await nats_client.connect(f"nats://nats:{settings.nats_port}")
    await nats_client.subscribe("chat.message.deleted", _on_message_deleted)
    yield
    await nats_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(files_router)
app.include_router(health_router)
app.include_router(internal_router)
