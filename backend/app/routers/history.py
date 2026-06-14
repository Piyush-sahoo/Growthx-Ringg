"""Real Ringg call history across all agents."""

from fastapi import APIRouter, HTTPException

from ..ringg import RinggError, ringg_client

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def call_history(page: int = 1, page_size: int = 25, agent_id: str | None = None) -> dict:
    """All real Ringg calls (optionally filtered by agent_id)."""
    try:
        return await ringg_client.call_history(page=page, page_size=page_size, agent_id=agent_id)
    except RinggError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
