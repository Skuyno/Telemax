"""Business logic for users."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.users import repository as users_repository
from app.users.models import User
from app.users.schemas import LoginRequest, RegisterRequest
from app.users.security import hash_password, verify_password


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Register a new user with a hashed password.

    Args:
        db: Async database session.
        data: Registration request body.

    Returns:
        User: The created user.
    """
    hashed_pwd = hash_password(data.password)
    return await users_repository.create_user(
        db, username=data.username, password_hash=hashed_pwd
    )


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> User | None:
    """Authenticate a user by username and password.

    Args:
        db: Async database session.
        data: Login request body.
    """
    user = await users_repository.get_user_by_username(db, data.username)
    if user and verify_password(data.password, user.password_hash):
        return user
    return None


async def get_user_profile(db: AsyncSession, data: UUID) -> User | None:
    """Get a user's profile by id.

    Args:
        db: Async database session.
        data: User's id.

    Returns:
        User | None: The user if found, otherwise None.
    """
    user = await users_repository.get_user_by_id(db, user_id=data)
    if user:
        return user
    return None
