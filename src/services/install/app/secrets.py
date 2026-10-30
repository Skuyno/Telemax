"""Random secret generation."""

import secrets


def generate_secret(length: int) -> str:
    """Generate a URL-safe random secret.

    Args:
        length: number of random bytes before base64 encoding (the
            resulting string is longer than this — token_urlsafe
            base64-encodes the raw bytes).

    Returns:
        str: a URL-safe random token.
    """
    return secrets.token_urlsafe(length)
