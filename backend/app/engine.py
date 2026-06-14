"""Branch engine (S2).

After a call completes, decide the branch from the structured `outcome` (falling
back to a Gemini classification of the transcript) and fire the branch's tool
action. S2 implements the ReportZen `activated_distracted` → send-checkout-link
action; the full graph-driven version arrives in S3.
"""

from __future__ import annotations

from . import llm, tools
from .models import CallRecord

REPORTZEN_BRANCHES = [
    "activated_distracted",
    "stakeholder_loop",
    "stuck_wall",
    "price_fit",
    "tourist",
    "callback",
]


def _upgrade_link(record: CallRecord) -> str:
    cav = record.custom_args_values or {}
    return cav.get("upgrade_link") or cav.get("retry_link") or "https://app.reportzen.example/upgrade"


async def ensure_outcome(record: CallRecord) -> str | None:
    """Use the captured outcome; if absent, classify the transcript with Gemini."""
    if record.outcome:
        return record.outcome
    if record.transcript:
        try:
            classified = llm.classify_outcome(record.transcript, REPORTZEN_BRANCHES)
        except llm.LLMError:
            classified = None
        if classified:
            record.outcome = classified
    return record.outcome


async def run_branch(record: CallRecord) -> list[dict]:
    """Fire the action(s) for the record's branch; append results to record.actions."""
    actions: list[dict] = []
    outcome = record.outcome

    if outcome == "activated_distracted":
        link = _upgrade_link(record)
        cav = record.custom_args_values or {}
        # Email the checkout link (Resend). Falls back to a Resend test inbox.
        if tools.email_configured():
            to = cav.get("email") or "delivered@resend.dev"
            try:
                res = await tools.send_email(
                    to=to,
                    subject=f"{record.customer_name}, your upgrade link",
                    html=(
                        f"<p>Hi {record.customer_name}, here is your upgrade link: "
                        f'<a href="{link}">{link}</a></p>'
                    ),
                )
                record.checkout_link_sent = True
                actions.append({"tool": "email", "status": "sent", "to": to, "id": res.get("id")})
            except tools.ToolError as exc:
                actions.append({"tool": "email", "status": "error", "error": str(exc)})
        else:
            actions.append({"tool": "email", "status": "skipped", "reason": "not_configured"})

        # WhatsApp the same link (Twilio sandbox), if configured.
        if tools.whatsapp_configured():
            try:
                res = await tools.send_whatsapp(
                    to=record.phone_number,
                    body=f"Hi {record.customer_name}, your upgrade link: {link}",
                )
                record.checkout_link_sent = True
                actions.append({"tool": "whatsapp", "status": "sent", "id": res.get("sid")})
            except tools.ToolError as exc:
                actions.append({"tool": "whatsapp", "status": "error", "error": str(exc)})
        else:
            actions.append({"tool": "whatsapp", "status": "skipped", "reason": "not_configured"})
    else:
        # S2: other branches are recorded; their actions land with the graph (S3).
        actions.append({"tool": "none", "status": "noop", "branch": outcome})

    record.actions = (record.actions or []) + actions
    return actions
