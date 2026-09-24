"""Service entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.admin.router import router as admin_router
from app.database import async_session_maker
from app.health.router import router as health_router
from app.internal.router import router as internal_router
from app.settings.router import router as settings_router
from app.users.router import router as users_router
from app.users.service import ensure_superuser_seeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Seed the superuser account on startup, if it doesn't exist yet."""
    async with async_session_maker() as db:
        await ensure_superuser_seeded(db)
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(health_router)
app.include_router(users_router)
app.include_router(internal_router)
app.include_router(settings_router)
app.include_router(admin_router)
