"""Outbound call trigger + call history endpoints."""

from fastapi import APIRouter, HTTPException

from ..models import CallRecord, CallStatus, OutboundCallRequest
from ..ringg import RinggError, ringg_client
from ..store import store

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=list[CallRecord])
def list_calls() -> list[CallRecord]:
    """Return all calls, newest first."""
    return store.list()


@router.get("/{call_id}", response_model=CallRecord)
def get_call(call_id: str) -> CallRecord:
    record = store.get(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return record


@router.post("", response_model=CallRecord, status_code=201)
async def create_call(payload: OutboundCallRequest) -> CallRecord:
    """Trigger a single outbound Ringg call and track it."""
    # Always include the customer name as a variable the prompt can reference.
    variables = {"customer_name": payload.customer_name, **payload.custom_args_values}

    record = CallRecord(
        customer_name=payload.customer_name,
        phone_number=payload.phone_number,
        custom_args_values=variables,
    )
    store.add(record)

    try:
        result = await ringg_client.place_outbound_call(
            phone_number=payload.phone_number,
            custom_args_values=variables,
        )
        record.ringg_call_id = (
            result.get("call_id") or result.get("id") or result.get("data", {}).get("call_id")
        )
        record.status = CallStatus.in_progress
    except RinggError as exc:
        record.status = CallStatus.failed
        record.analysis = {"error": str(exc)}
        store.update(record)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return store.update(record)
