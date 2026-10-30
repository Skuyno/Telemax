"""Liveness route — no database, no dependencies to check."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Report liveness.

    Returns:
        dict[str, str]: a static ok status.
    """
    return {"status": "ok"}
