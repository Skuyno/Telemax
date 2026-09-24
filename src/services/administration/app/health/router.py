"""Health check route.

No database of its own, so unlike other services this has no /health/db —
just a liveness check.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Basic liveness check.

    Returns:
        dict[str, str]: A fixed status payload.
    """
    return {"status": "ok"}
