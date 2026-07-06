"""Password hashing functions."""

from pwdlib import PasswordHash

pwd_context = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Provide a password hash for the given password.

    Args:
        password: the password to hash.

    Returns:
        str: the hashed password.
    """
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.

    Args:
        password: the password to verify.
        password_hash: the hash to verify against.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(password, password_hash)
