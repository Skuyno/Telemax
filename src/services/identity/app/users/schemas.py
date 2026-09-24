"""Pydantic schemas for users."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
    avatar_url: str | None
    created_at: datetime
    role: str


class UpdateProfileRequest(BaseModel):
    """Partial update of the current user's profile.

    Fields left unset are unchanged. `avatar_url` isn't settable here —
    it's only ever set by the dedicated avatar upload/delete endpoints
    (`PUT`/`DELETE /me/avatar`), which also own the actual image blob.
    """

    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    email: str | None = Field(default=None, min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def _validate_email_shape(cls, value: str | None) -> str | None:
        """Reject an email that doesn't look like one.

        Raises:
            ValueError: If the value doesn't match a basic `x@y.z` shape.
        """
        if value is not None and not _EMAIL_PATTERN.match(value):
            raise ValueError("Invalid email format")
        return value


class ChangePasswordRequest(BaseModel):
    """Request to change the current user's own password.

    Requires the current password even though the caller is already
    authenticated, so a stolen short-lived access token alone can't be
    used to lock the real owner out of their account.
    """

    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class ResetPasswordRequest(BaseModel):
    """Request to reset the current user's own password from settings.

    Unlike ChangePasswordRequest, this doesn't require the current
    password — a deliberate, simpler flow for the settings page. The
    caller must still be authenticated (a valid access token).
    """

    new_password: str = Field(min_length=8, max_length=256)


class CreateAccountRequest(BaseModel):
    """Request to create an admin or user account (an admin-management action).

    Distinct from RegisterRequest: this carries a target role and is only
    reachable by an already-authenticated admin/superuser, whereas
    RegisterRequest is the public self-service signup (always "user").
    """

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=256)
    role: str = Field(pattern="^(admin|user)$")


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
