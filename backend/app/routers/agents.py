"""Agent discovery — list callable Ringg agents and their custom variables.

Drives the dynamic "New outbound call" form: the fields rendered depend on the
selected agent's custom_variables.
"""

from fastapi import APIRouter, HTTPException

from ..catalog import TOOL_CATALOG
from ..ringg import RinggError, ringg_client

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/tools/catalog")
def tool_catalog() -> dict:
    """The full catalog of available tools (custom + Ringg built-in)."""
    return TOOL_CATALOG


@router.get("")
async def list_agents() -> list[dict]:
    try:
        return await ringg_client.list_agents()
    except RinggError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{agent_id}/variables")
async def agent_variables(agent_id: str) -> dict:
    try:
        return {"agent_id": agent_id, "variables": await ringg_client.get_agent_variables(agent_id)}
    except RinggError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{agent_id}/calls")
async def agent_calls(agent_id: str, page: int = 1, page_size: int = 25) -> dict:
    """Real Ringg call history for one agent."""
    try:
        return await ringg_client.call_history(page=page, page_size=page_size, agent_id=agent_id)
    except RinggError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{agent_id}/tools")
async def agent_tools(agent_id: str) -> dict:
    """The tools actually attached to this agent (live), by phase."""
    try:
        return await ringg_client.get_agent_tools(agent_id)
    except RinggError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
