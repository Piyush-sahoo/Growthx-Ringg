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


def video_configured() -> bool:
    """The recap-video tool delivers via Resend, so it shares email config."""
    return bool(get_settings().resend_api_key)


def telegram_configured() -> bool:
    s = get_settings()
    return bool(s.telegram_bot_token and s.telegram_chat_id)


def slack_configured() -> bool:
    return bool(get_settings().slack_webhook_url)


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


async def send_telegram(*, text: str, chat_id: str | None = None) -> dict:
    """Send a Telegram message via the Bot API. Unlimited, no DLT — the
    GrowthX-recommended realtime channel for checkout links / summaries."""
    s = get_settings()
    if not s.telegram_bot_token:
        raise ToolError("TELEGRAM_BOT_TOKEN not set")
    target = chat_id or s.telegram_chat_id
    if not target:
        raise ToolError("TELEGRAM_CHAT_ID not set")
    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            url,
            json={
                "chat_id": target,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
        )
    if r.status_code >= 400:
        raise ToolError(f"Telegram {r.status_code}: {r.text}")
    return r.json()


async def send_slack(*, text: str) -> dict:
    """Post to a Slack channel via an incoming webhook — internal escalation
    (stuck walls, urgent flags, wall patterns for product)."""
    s = get_settings()
    if not s.slack_webhook_url:
        raise ToolError("SLACK_WEBHOOK_URL not set")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(s.slack_webhook_url, json={"text": text})
    if r.status_code >= 400:
        raise ToolError(f"Slack {r.status_code}: {r.text}")
    return {"status": "ok"}


async def send_recap_video(*, to: str, html: str) -> dict:
    """Email a personalized HyperFrames recap via Resend (HTML embedded inline).

    Returns the Resend response (includes ``id``). Garnish / off the live path.
    """
    return await send_email(
        to=to,
        subject="Your ReportZen recap",
        html=html,
    )
