"""FastAPI dependencies."""

from uuid import UUID

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import settings


def get_authorization_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> UUID:
    """Verify the access token and extract the user id.

    Args:
        credentials: Bearer token extracted from the Authorization header.

    Returns:
        UUID: The authenticated user's id (JWT `sub` claim).

    Raises:
        HTTPException: 401 if the token is missing, invalid, expired, or not
            an access token.
    """
    try:
        if credentials is None:
            raise jwt.InvalidTokenError
        decoded = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        if decoded["type"] != "access" or credentials.scheme != "Bearer":
            raise jwt.InvalidTokenError
        return UUID(decoded["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401)
