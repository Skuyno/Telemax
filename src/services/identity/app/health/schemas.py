"""Pydantic schemas for health checks."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Basic response."""

    description: str
