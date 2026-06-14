"""Health and readiness endpoints."""

from fastapi import APIRouter

from ..config import get_settings
from ..ringg import ringg_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "ringg_configured": ringg_client.configured,
    }
