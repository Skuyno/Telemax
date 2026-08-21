"""JWT creation for the identity service."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.config import settings


def create_access_token(user_id: UUID) -> str:
    """Create a short-lived access token.

    Args:
        user_id: Id of the user the token is issued for.

    Returns:
        str: Signed JWT with sub, exp and type claims.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: UUID, token_version: int) -> str:
    """Create a long-lived refresh token.

    Args:
        user_id: Id of the user the token is issued for.
        token_version: Version of the user refresh token

    Returns:
        str: Signed JWT with sub, exp and type claims.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "type": "refresh",
        "ver": token_version,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
