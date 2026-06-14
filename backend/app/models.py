"""Pydantic models for requests, responses and stored records."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


class CallStatus(str, Enum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class OutboundCallRequest(BaseModel):
    """Payload to trigger a single outbound Ringg call."""

    customer_name: str = Field(..., examples=["Asha Rao"])
    phone_number: str = Field(..., examples=["+919812345678"])
    # Per-row variables that map to @{{variable}} placeholders in the Ringg prompt.
    custom_args_values: dict[str, Any] = Field(default_factory=dict)


class CallRecord(BaseModel):
    """A call as tracked by this backend."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    customer_name: str
    phone_number: str
    custom_args_values: dict[str, Any] = Field(default_factory=dict)
    status: CallStatus = CallStatus.queued
    ringg_call_id: str | None = None
    transcript: str | None = None
    recording_url: str | None = None
    analysis: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class RinggWebhookEvent(BaseModel):
    """Subset of the Ringg post-call webhook payload we care about.

    See https://docs.ringg.ai/webhooks/payloads — fields are optional because
    Ringg sends different shapes for different events (call_completed, etc).
    """

    event: str | None = None
    # Ringg sends `event_type` (e.g. all_processing_completed, call_completed,
    # recording_completed, platform_analysis_completed, client_analysis_completed).
    event_type: str | None = None
    call_id: str | None = None
    status: str | None = None
    transcript: str | None = None
    recording_url: str | None = None
    analysis: dict[str, Any] | None = None
    # Echoed-back variables we sent when placing the call.
    custom_args_values: dict[str, Any] | None = None
