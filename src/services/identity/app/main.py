"""Service entry point."""
from fastapi import FastAPI

from app.health.router import router as health_router
from app.users.router import router as users_router

app = FastAPI()

app.include_router(health_router)
app.include_router(users_router)
