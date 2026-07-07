"""Business logic for user registration."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.users import repository as users_repository
from app.users.models import User
from app.users.schemas import RegisterRequest
from app.users.security import hash_password


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
