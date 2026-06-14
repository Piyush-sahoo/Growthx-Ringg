"""Outbound call trigger + call history endpoints."""

from fastapi import APIRouter, HTTPException

from .. import memory
from ..models import CallRecord, CallStatus, OutboundCallRequest
from ..ringg import RinggError, ringg_client
from ..store import store

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=list[CallRecord])
async def list_calls() -> list[CallRecord]:
    """Return all calls, newest first."""
    return await store.list()


@router.get("/{call_id}", response_model=CallRecord)
async def get_call(call_id: str) -> CallRecord:
    record = await store.get(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return record


@router.post("/{call_id}/dispatch", response_model=CallRecord)
async def dispatch_call(call_id: str) -> CallRecord:
    """Place a queued follow-up call (the next call in a workflow) on demand."""
    record = await store.get(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found")

    # Use the agent bound to this call's workflow node if the workflow is deployed.
    agent_id = None
    if record.workflow_id and record.current_node_id:
        wf = await store.get_workflow(record.workflow_id)
        if wf:
            node = next(
                (n for n in wf.get("nodes", []) if n.get("id") == record.current_node_id), None
            )
            if node:
                agent_id = node.get("agent_id")

    try:
        result = await ringg_client.place_outbound_call(
            name=record.customer_name,
            phone_number=record.phone_number,
            custom_args_values=record.custom_args_values,
            assistant_id=agent_id,
        )
        record.ringg_call_id = (
            result.get("call_id") or result.get("id") or (result.get("data") or {}).get("call_id")
        )
        record.status = CallStatus.in_progress
    except RinggError as exc:
        record.status = CallStatus.failed
        record.analysis = {**(record.analysis or {}), "dispatch_error": str(exc)}
        await store.update(record)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return await store.update(record)


@router.post("", response_model=CallRecord, status_code=201)
async def create_call(payload: OutboundCallRequest) -> CallRecord:
    """Trigger a single outbound Ringg call and track it."""
    # Load/create the contact, refresh its `now` from the request, and persist.
    contact = await store.get_contact(payload.phone_number) or memory.new_contact(
        payload.phone_number, payload.customer_name, memory.now_from(payload.custom_args_values)
    )
    contact.now.update(memory.now_from(payload.custom_args_values))
    await store.save_contact(contact)

    # Compile three-layer memory into custom_args_values; explicit request values win.
    variables = {
        "customer_name": payload.customer_name,
        **memory.compile_memory(contact),
        **payload.custom_args_values,
    }

    record = CallRecord(
        customer_name=payload.customer_name,
        phone_number=payload.phone_number,
        custom_args_values=variables,
    )
    await store.add(record)

    try:
        result = await ringg_client.place_outbound_call(
            name=payload.customer_name,
            phone_number=payload.phone_number,
            custom_args_values=variables,
            assistant_id=payload.agent_id,
        )
        record.ringg_call_id = (
            result.get("call_id")
            or result.get("id")
            or (result.get("data") or {}).get("call_id")
        )
        record.status = CallStatus.in_progress
    except RinggError as exc:
        record.status = CallStatus.failed
        record.analysis = {"error": str(exc)}
        await store.update(record)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return await store.update(record)
