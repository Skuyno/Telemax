"""Pydantic schemas for users."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RegisterRequest(BaseModel):
    """Registration request."""

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=256)


class RegisterResponse(BaseModel):
    """Registration response."""

    model_config = ConfigDict(from_attributes=True)
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
    """Current user's profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    phone: str | None
    display_name: str | None
    created_at: datetime


class UserSearchRequest(BaseModel):
    """Search request for the user directory.

    At least one of `tag`, `email`, `phone`, `name`, `query` must be set.
    `tag` matches only a prefix of the username (a leading "@" is ignored
    if present); `email`, `phone`, and `name` match any substring; `query`
    matches a substring against email, phone, or display_name all at once
    (but never against tag/username). Matching is always case-insensitive.
    When several fields are given together, all of them must match.
    """

    tag: str | None = Field(default=None, min_length=1, max_length=33)
    email: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    query: str | None = Field(default=None, min_length=1, max_length=255)
    limit: int = Field(gt=0)

    @model_validator(mode="after")
    def _require_at_least_one_filter(self) -> "UserSearchRequest":
        """Reject a search with no filter criteria at all.

        Raises:
            ValueError: If tag, email, phone, name, and query are all unset.
        """
        if not any([self.tag, self.email, self.phone, self.name, self.query]):
            raise ValueError(
                "At least one of tag, email, phone, name, query must be provided"
            )
        return self
