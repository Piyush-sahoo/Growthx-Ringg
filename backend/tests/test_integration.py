"""Live integration tests — hit the real Ringg + Gemini APIs.

Marked `integration`; skipped automatically when keys are absent. These make real
(read-only / classification) network calls. They do NOT place outbound phone calls.
Run just these with:  pytest -m integration
"""

import httpx
import pytest

from app import llm, tools
from app.config import get_settings

settings = get_settings()

BRANCHES = [
    "activated_distracted",
    "stakeholder_loop",
    "stuck_wall",
    "price_fit",
    "tourist",
    "callback",
]


@pytest.mark.integration
@pytest.mark.skipif(not settings.ringg_api_key, reason="RINGG_API_KEY not set")
def test_ringg_workspace_live():
    """The Ringg key authenticates and the workspace reports credits."""
    resp = httpx.get(
        f"{settings.ringg_base_url.rstrip('/')}/workspace",
        headers={"X-API-KEY": settings.ringg_api_key},
        timeout=30,
    )
    assert resp.status_code == 200
    info = resp.json().get("workspace_info", {})
    assert "credits" in info or "total_available_credits" in info


@pytest.mark.integration
@pytest.mark.skipif(not settings.ringg_api_key, reason="RINGG_API_KEY not set")
def test_ringg_has_outbound_agent_and_number():
    """There is at least one outbound agent and one caller number to run with."""
    h = {"X-API-KEY": settings.ringg_api_key}
    base = settings.ringg_base_url.rstrip("/")
    agents = httpx.get(f"{base}/agent/all", headers=h, timeout=30).json()
    agent_list = agents.get("data", {}).get("agents", []) if isinstance(agents, dict) else agents
    assert any(a.get("agent_type") == "outbound" for a in agent_list)

    numbers = httpx.get(f"{base}/workspace/numbers", headers=h, timeout=30).json()
    assert numbers.get("workspace_numbers")


@pytest.mark.integration
@pytest.mark.skipif(not settings.gemini_api_key, reason="GEMINI_API_KEY not set")
def test_gemini_classify_live():
    """Gemini structured output returns a valid branch for a clear transcript."""
    out = llm.classify_outcome(
        "I tried importing our client data, it failed, and honestly I stopped using it.",
        BRANCHES,
    )
    assert out in BRANCHES
    assert out == "stuck_wall"


@pytest.mark.integration
@pytest.mark.skipif(not settings.resend_api_key, reason="RESEND_API_KEY not set")
async def test_resend_send_live():
    """Resend accepts a real send to its test inbox and returns an id."""
    res = await tools.send_email(
        to="delivered@resend.dev",
        subject="FlowForge live test",
        html='<p>Upgrade: <a href="https://app.reportzen.example/upgrade">link</a></p>',
    )
    assert res.get("id")


@pytest.mark.integration
@pytest.mark.skipif(not tools.whatsapp_configured(), reason="Twilio not configured")
def test_twilio_auth_live():
    """Twilio Account SID + Auth Token authenticate against the API."""
    sid = settings.twilio_account_sid
    resp = httpx.get(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
        auth=(sid, settings.twilio_auth_token),
        timeout=30,
    )
    assert resp.status_code == 200
    assert resp.json().get("status") == "active"


@pytest.mark.integration
@pytest.mark.skipif(not settings.ringg_api_key, reason="RINGG_API_KEY not set")
def test_ringg_credits_live():
    from fastapi.testclient import TestClient

    from app.main import app

    resp = TestClient(app).get("/workflows/credits")
    assert resp.status_code == 200
    assert resp.json()["credits"] >= 0


@pytest.mark.integration
@pytest.mark.skipif(
    not (settings.ringg_api_key and settings.ringg_assistant_id),
    reason="needs RINGG_API_KEY + RINGG_ASSISTANT_ID for the A-lite fallback",
)
def test_deploy_live_subscribes_real_agent():
    """Live deploy: create-agent may be KYC-gated (falls back), but the webhook
    subscription on the resulting real agent succeeds."""
    from fastapi.testclient import TestClient

    from app.main import app

    resp = TestClient(app).post(
        "/workflows/deploy", json={"template_id": "reportzen-trial-to-paid"}
    )
    assert resp.status_code == 200
    agent = resp.json()["deployment"]["agents"][0]
    assert agent["agent_id"]  # created, or reused via A-lite fallback
    assert agent["subscribed"] == "subscribed"
