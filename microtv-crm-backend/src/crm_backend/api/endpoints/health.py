"""Healthcheck endpoints."""

from fastapi import APIRouter


router = APIRouter(tags=["system"])


@router.get("/health")
def healthcheck() -> dict[str, str]:
    """Report service health.

    Returns:
        dict[str, str]: Static health payload.
    """

    return {"status": "ok"}
