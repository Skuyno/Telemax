"""Short-lived signed links for authorization-header-less file access.

A browser can't attach an Authorization header to a <video>/<audio> src
attribute, so a signed link stands in as the credential instead: whoever
requested it (POST .../link) has already passed the normal chat-membership
check once, and the signature + expiry alone are enough to authorize the
actual download afterward — no user id involved at that point.
"""

import hashlib
import hmac
import time

from app.config import settings

LINK_TTL_SECONDS = 300


def _signature(file_id: str, exp: int) -> str:
    """Compute the HMAC-SHA256 signature for a (file_id, exp) pair.

    Args:
        file_id: the file's id, as a string.
        exp: unix timestamp the link expires at.

    Returns:
        str: hex-encoded HMAC digest.
    """
    message = f"{file_id}:{exp}".encode()
    key = settings.link_signing_secret.encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def issue_link(file_id: str) -> tuple[str, int]:
    """Create a signature and expiry for a one-time download link.

    Args:
        file_id: the file's id, as a string.

    Returns:
        tuple[str, int]: (signature, expires_at unix timestamp).
    """
    exp = int(time.time()) + LINK_TTL_SECONDS
    return _signature(file_id, exp), exp


def verify_link(file_id: str, sig: str, exp: int) -> bool:
    """Check whether a signature is valid and not expired.

    Args:
        file_id: the file's id, as a string.
        sig: the signature to check.
        exp: the claimed expiry, unix timestamp.

    Returns:
        bool: True if the signature matches and hasn't expired.
    """
    if exp < int(time.time()):
        return False
    expected = _signature(file_id, exp)
    return hmac.compare_digest(expected, sig)
