"""FastAPI dependencies."""

from uuid import UUID

from fastapi import Header


async def get_current_user_id(x_user_id: UUID = Header(...)) -> UUID:
    """Trust the user id set by API Gateway."""
    return x_user_id
