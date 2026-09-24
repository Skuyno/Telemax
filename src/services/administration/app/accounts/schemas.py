"""Pydantic schemas for account management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateAccountRequest(BaseModel):
    """Request to create an admin or user account.

    role never allows "superuser" — that account is provisioned once,
    automatically, by identity itself at startup; it can't be created
    through this API no matter who's asking.
    """

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=256)
    role: str = Field(pattern="^(admin|user)$")


class AccountResponse(BaseModel):
    """An account's public profile, as returned by identity."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    phone: str | None
    display_name: str | None
    avatar_url: str | None
    created_at: datetime
    role: str


class UsernameAvailableResponse(BaseModel):
    """Whether a username is free to create an account with."""

    available: bool
