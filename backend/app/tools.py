"""Tool runners — side effects the workflow fires on a branch.

S2 ships two: email (Resend) and WhatsApp (Twilio sandbox). Each is config-gated;
callers check ``*_configured()`` and a disabled tool reports a skipped result
rather than raising.
"""

from __future__ import annotations

import httpx

from .config import get_settings


class ToolError(RuntimeError):
    pass


def email_configured() -> bool:
    return bool(get_settings().resend_api_key)


def whatsapp_configured() -> bool:
    s = get_settings()
    return bool(s.twilio_account_sid and s.twilio_auth_token and s.twilio_whatsapp_from)


async def send_email(*, to: str, subject: str, html: str) -> dict:
    """Send an email via Resend. Returns the Resend response (includes ``id``)."""
    s = get_settings()
    if not s.resend_api_key:
        raise ToolError("RESEND_API_KEY not set")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {s.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={"from": s.resend_from, "to": [to], "subject": subject, "html": html},
        )
    if r.status_code >= 400:
        raise ToolError(f"Resend {r.status_code}: {r.text}")
    return r.json()


async def send_whatsapp(*, to: str, body: str) -> dict:
    """Send a WhatsApp message via the Twilio sandbox. ``to`` is E.164 (no prefix)."""
    s = get_settings()
    if not whatsapp_configured():
        raise ToolError("Twilio WhatsApp not configured")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Messages.json"
    data = {"From": s.twilio_whatsapp_from, "To": f"whatsapp:{to}", "Body": body}
    async with httpx.AsyncClient(timeout=30, auth=(s.twilio_account_sid, s.twilio_auth_token)) as c:
        r = await c.post(url, data=data)
    if r.status_code >= 400:
        raise ToolError(f"Twilio {r.status_code}: {r.text}")
    return r.json()
