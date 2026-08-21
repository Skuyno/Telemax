"""Tests for JWT creation functions."""

from uuid import uuid4

import jwt
import pytest

from app.config import settings
from app.users.tokens import create_access_token, create_refresh_token


def test_access_token_roundtrip() -> None:
    """Access token decodes with the app secret and carries sub and type."""
    user_id = uuid4()

    token = create_access_token(user_id)
    dec_token = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )

    assert dec_token["type"] == "access"
    assert dec_token["sub"] == str(user_id)


def test_refresh_token_roundtrip() -> None:
    """Refresh token decodes with the app secret and carries sub and type."""
    user_id = uuid4()
    token_version = 0

    token = create_refresh_token(user_id, token_version)
    dec_token = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )

    assert dec_token["type"] == "refresh"
    assert dec_token["sub"] == str(user_id)


def test_refresh_lives_longer_than_access() -> None:
    """Refresh token expires later than an access token issued together."""
    user_id = uuid4()
    token_version = 0

    a_token = create_access_token(user_id)
    r_token = create_refresh_token(user_id, token_version)

    a_dec_token = jwt.decode(
        a_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )

    r_dec_token = jwt.decode(
        r_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )

    assert a_dec_token["exp"] < r_dec_token["exp"]


def test_wrong_secret_rejected() -> None:
    """Token signed with the app secret must not decode with another secret."""
    user_id = uuid4()

    token = create_access_token(user_id)

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(
            token,
            "aboba-aboba-aboba-aboba-aboba-aboba-aboba-aboba",
            algorithms=[settings.jwt_algorithm],
        )


def test_expired_token_rejected(monkeypatch) -> None:
    """Token created alreadt expired must be rejected on decode."""
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)

    token = create_access_token(uuid4())

    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
