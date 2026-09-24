"""Service entry point."""

from fastapi import FastAPI

from app.accounts.router import router as accounts_router
from app.health.router import router as health_router

app = FastAPI()

app.include_router(health_router)
app.include_router(accounts_router)
