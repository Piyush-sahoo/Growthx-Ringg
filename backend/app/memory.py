"""Three-layer memory (S5).

Compiles a contact's Context Object (now / before / rules) into Ringg
`custom_args_values` before a call, and writes each call's outcome back into
`before` after the webhook. This is what lets a follow-up agent open by
referencing the prior wall and promise.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .models import CallRecord, ContextObject

# The `rules` layer for ReportZen (the business policy the agent must apply).
REPORTZEN_RULES = {
    "pricing": "Studio 5000/mo up to 5 client connections; Pro 12000/mo past 10.",
    "extension_policy": "Extend only for a stuck evaluation with a named blocker.",
    "never": [
        "never invent urgency",
        "never extend reflexively",
        "never go around the evaluator",
        "never push annual on undecided monthly",
        "no discount reflex",
    ],
}


TRIAL_FIELDS = ["trial_id", "days_left", "accounts_connected", "reports_sent", "plan_fit"]


def now_from(cav: dict) -> dict:
    """Extract the trial fields from custom_args_values into the `now` layer."""
    return {k: cav.get(k) for k in TRIAL_FIELDS if cav.get(k) is not None}


def new_contact(phone_number: str, customer_name: str, now: dict | None = None) -> ContextObject:
    return ContextObject(
        phone_number=phone_number,
        customer_name=customer_name,
        now=now or {},
        before=[],
        rules=dict(REPORTZEN_RULES),
    )


def _activation_summary(now: dict) -> str:
    accounts = now.get("accounts_connected")
    reports = now.get("reports_sent")
    if accounts or reports:
        return f"{accounts or 0} client accounts connected, {reports or 0} white-label reports sent"
    return "activation details unknown"


def _memory_summary(contact: ContextObject) -> str:
    if not contact.before:
        return "First outreach. " + _activation_summary(contact.now) + "."
    last = contact.before[-1]
    parts = [f"Prior call outcome: {last.get('outcome')}"]
    if last.get("wall"):
        parts.append(f"wall: {last['wall']}")
    if last.get("promise"):
        parts.append(f"they promised: {last['promise']}")
    if last.get("extension_granted"):
        parts.append(f"extended {last.get('extension_days', '?')} days")
    return "; ".join(parts) + "."


def compile_memory(contact: ContextObject, *, days_left_override: str | None = None) -> dict:
    """Build the custom_args_values the agent prompt references."""
    now = contact.now
    last = contact.before[-1] if contact.before else {}
    days_left = days_left_override if days_left_override is not None else now.get("days_left", "")
    return {
        "callee_name": contact.customer_name,
        "mobile_number": contact.phone_number,
        "trial_id": str(now.get("trial_id", "")),
        "days_left": str(days_left),
        "accounts_connected": str(now.get("accounts_connected", "")),
        "reports_sent": str(now.get("reports_sent", "")),
        "plan_fit": str(now.get("plan_fit", "")),
        # Ringg has no memory feature — cross-call memory is passed as these variables,
        # written back by the webhook after each call.
        "last_call_outcome": str(last.get("outcome") or "none"),
        "last_call_date": str(last.get("at") or ""),
        "last_promise": str(last.get("promise") or "none (first call)"),
        "memory_summary": _memory_summary(contact),
    }


def record_outcome(contact: ContextObject, record: CallRecord) -> ContextObject:
    """Append this call's result to `before` and refresh `now` (the write-back)."""
    analysis = record.analysis or {}
    entry = {
        "at": datetime.now(UTC).isoformat(),
        "call_id": record.id,
        "outcome": record.outcome,
        "wall": analysis.get("wall_description"),
        "promise": analysis.get("last_promise")
        or analysis.get("promise")
        or analysis.get("commitment"),
        "extension_granted": bool(analysis.get("extension_granted")),
        "extension_days": analysis.get("extension_days"),
        "days_left": contact.now.get("days_left"),
    }
    contact.before.append(entry)
    contact.now["last_outcome"] = record.outcome
    if analysis.get("plan_fit"):
        contact.now["plan_fit"] = analysis["plan_fit"]
    contact.updated_at = datetime.now(UTC)
    return contact
