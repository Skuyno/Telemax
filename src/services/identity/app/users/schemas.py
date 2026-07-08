"""Pydantic schemas for auth."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    """Registration request."""

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=256)


class RegisterResponse(BaseModel):
    """Registration response."""

    model_config = {"from_attributes": True}
    id: UUID


class LoginRequest(BaseModel):
    """Login request."""

    username: str = Field(max_length=256)
    password: str = Field(max_length=256)


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRequest(BaseModel):
    """Token request."""

    refresh_token: str


class UserResponse(BaseModel):
    """Current user's profile."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    display_name: str | None
    created_at: datetime

