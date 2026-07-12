"""Test the security functions for password hashing and verification."""
from app.users.security import hash_password, verify_password


def test_hash_differs_from_password() -> None:
    """Verify that hashing a password produces a different string."""
    password = "password"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$argon2")


def test_verify_correct_password() -> None:
    """Verify that the password matches its hash."""
    password = "password"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_wrong_password() -> None:
    """Verify that the password does not match a different hash."""
    password = "password"
    hashed = hash_password(password)
    assert verify_password("aboba", hashed) is False


def test_same_password_different_hashed() -> None:
    """Verify that hashing the same password twice produces different hashes."""
    password = "password"
    hashed1 = hash_password(password)
    hashed2 = hash_password(password)
    assert hashed1 != hashed2
