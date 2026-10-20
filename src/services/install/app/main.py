"""Service entry point.

Only the health route exists so far — manifest discovery (app/discovery.py,
app/schema.py) is wired up, but the install form, secret generation/writing
and the docker compose runner land in later steps.
"""

from fastapi import FastAPI

from app.health.router import router as health_router

app = FastAPI()

app.include_router(health_router)
