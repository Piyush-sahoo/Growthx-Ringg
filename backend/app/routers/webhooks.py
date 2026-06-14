"""Ringg AI post-call webhook receiver.

Ringg posts call results here after each call (call_completed): transcript,
recording URL and analysis. Docs: https://docs.ringg.ai/webhooks/payloads
"""

from fastapi import APIRouter, Header, HTTPException

from ..config import get_settings
from ..models import CallRecord, CallStatus, RinggWebhookEvent
from ..store import store

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/ringg")
async def ringg_webhook(
    event: RinggWebhookEvent,
    x_webhook_secret: str | None = Header(default=None),
) -> dict:
    """Receive a Ringg call event and merge it into the matching call record."""
    settings = get_settings()

    # Optional shared-secret check. Only enforced if a secret is configured.
    if settings.ringg_webhook_secret:
        if x_webhook_secret != settings.ringg_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    record: CallRecord | None = None
    if event.call_id:
        record = store.get_by_ringg_id(event.call_id)

    # Fall back to matching on phone number from echoed variables.
    if record is None and event.custom_args_values:
        phone = event.custom_args_values.get("phone_number")
        if phone:
            record = next(
                (r for r in store.list() if r.phone_number == phone), None
            )

    if record is None:
        # Unknown call — store a standalone record so nothing is lost.
        record = CallRecord(
            customer_name=(event.custom_args_values or {}).get("customer_name", "unknown"),
            phone_number=(event.custom_args_values or {}).get("phone_number", "unknown"),
            ringg_call_id=event.call_id,
        )
        store.add(record)

    if event.transcript is not None:
        record.transcript = event.transcript
    if event.recording_url is not None:
        record.recording_url = event.recording_url
    if event.analysis is not None:
        record.analysis = event.analysis
    if event.call_id and not record.ringg_call_id:
        record.ringg_call_id = event.call_id

    # Map Ringg event_type / status to our enum.
    event_name = (event.event_type or event.event or "").lower()
    completion_events = {"call_completed", "all_processing_completed"}
    if event_name in completion_events or (event.status or "").lower() in {
        "completed",
        "ended",
        "success",
    }:
        record.status = CallStatus.completed
    elif (event.status or "").lower() in {"failed", "error"}:
        record.status = CallStatus.failed

    store.update(record)
    return {"ok": True, "call_id": record.id}
