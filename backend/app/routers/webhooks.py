"""Ringg AI post-call webhook receiver.

Ringg posts call events here keyed by `event_type` (call_started, call_completed,
recording_completed, platform_analysis_completed, client_analysis_completed,
all_processing_completed). The `transcript` is an array of turn objects; the
structured `outcome` rides in the custom (client) analysis.
Docs: https://docs.ringg.ai/webhooks/payloads
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException

from ..config import get_settings
from ..models import CallRecord, CallStatus, RinggWebhookEvent, transcript_to_text
from ..store import store

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

COMPLETION_EVENTS = {"call_completed", "all_processing_completed"}


def _extract_outcome(event: RinggWebhookEvent) -> str | None:
    """Pull the structured outcome from whichever analysis block carries it."""
    for src in (event.client_analysis, event.analysis, event.platform_analysis):
        if isinstance(src, dict):
            outcome = src.get("outcome") or src.get("trial_status")
            if outcome:
                return outcome
    return None


@router.post("/ringg")
async def ringg_webhook(
    event: RinggWebhookEvent,
    x_webhook_secret: str | None = Header(default=None),
) -> dict:
    """Receive a Ringg call event and merge it into the matching call record."""
    settings = get_settings()
    if settings.ringg_webhook_secret and x_webhook_secret != settings.ringg_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    event_name = (event.event_type or event.event or "").lower()

    # Dedupe on call_id + event_type (Ringg retries). 2xx on duplicates.
    if event.call_id and await store.seen_event(event.call_id, event_name):
        return {"ok": True, "deduped": True}

    # Match an existing record by Ringg call id, then by echoed phone number.
    record: CallRecord | None = None
    if event.call_id:
        record = await store.get_by_ringg_id(event.call_id)
    if record is None and event.custom_args_values:
        phone = event.custom_args_values.get("phone_number") or event.custom_args_values.get(
            "mobile_number"
        )
        if phone:
            record = next((r for r in await store.list() if r.phone_number == phone), None)
    if record is None:
        cav = event.custom_args_values or {}
        record = CallRecord(
            customer_name=cav.get("customer_name") or cav.get("callee_name", "unknown"),
            phone_number=cav.get("phone_number") or cav.get("mobile_number", "unknown"),
            ringg_call_id=event.call_id,
        )
        await store.add(record)

    if event.transcript is not None:
        record.transcript = transcript_to_text(event.transcript)
        if isinstance(event.transcript, list):
            record.transcript_turns = event.transcript
    if event.recording_url is not None:
        record.recording_url = event.recording_url
    if isinstance(event.analysis, dict):
        record.analysis = event.analysis
    outcome = _extract_outcome(event)
    if outcome:
        record.outcome = outcome
    if event.call_id and not record.ringg_call_id:
        record.ringg_call_id = event.call_id

    if event_name in COMPLETION_EVENTS or (event.status or "").lower() in {
        "completed",
        "ended",
        "success",
    }:
        record.status = CallStatus.completed
    elif (event.status or "").lower() in {"failed", "error"}:
        record.status = CallStatus.failed

    record.updated_at = datetime.now(UTC)
    await store.update(record)
    return {"ok": True, "call_id": record.id, "outcome": record.outcome}
