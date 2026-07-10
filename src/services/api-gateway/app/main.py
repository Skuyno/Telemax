"""API Gateway service entrypoint."""

from fastapi import FastAPI

from app.router import router

app = FastAPI()

app.include_router(router)
