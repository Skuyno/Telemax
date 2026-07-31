"""Service entry point."""

from fastapi import FastAPI

from app.chats.router import router as chats_router
from app.health.router import router as health_router

app = FastAPI()

app.include_router(chats_router)
app.include_router(health_router)
