"""Service entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.chats.router import router as chats_router
from app.config import settings
from app.events import nats_client
from app.health.router import router as health_router
from app.internal.router import router as internal_router
from app.settings.router import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan resources like NATS connection."""
    await nats_client.connect(f"nats://nats:{settings.nats_port}")
    yield
    await nats_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(chats_router)
app.include_router(health_router)
app.include_router(internal_router)
app.include_router(settings_router)

