"""Service entry point."""

from fastapi import FastAPI

from app.chats import router as chats_router

app = FastAPI()

app.include_router(chats_router)
