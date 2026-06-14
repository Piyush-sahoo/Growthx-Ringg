"""S4: deploy graph -> Ringg (Ringg client faked at the boundary)."""

from fastapi.testclient import TestClient

from app import ringg as ringg_module
from app.main import app

client = TestClient(app)


def _fake_ringg(monkeypatch):
    counters = {"create": 0, "subscribe": 0}

    async def fake_create(payload):
        counters["create"] += 1
        assert payload["primary_language"]  # built a real payload
        assert payload["voice_id"]
        return f"agent-{counters['create']}"

    async def fake_subscribe(**kwargs):
        counters["subscribe"] += 1
        assert kwargs["callback_url"].endswith("/webhooks/ringg")
        return {"ok": True}

    async def fake_resolve_voice(language):
        return "voice-test-id"

    monkeypatch.setattr(ringg_module.ringg_client, "create_agent", fake_create)
    monkeypatch.setattr(ringg_module.ringg_client, "subscribe_webhooks", fake_subscribe)
    monkeypatch.setattr(ringg_module.ringg_client, "resolve_voice_id", fake_resolve_voice)
    return counters


def test_deploy_creates_one_agent_per_call_node(monkeypatch):
    counters = _fake_ringg(monkeypatch)
    resp = client.post("/workflows/deploy", json={"template_id": "reportzen-trial-to-paid"})
    assert resp.status_code == 200

    agents = resp.json()["deployment"]["agents"]
    assert len(agents) == 1  # ReportZen has one call node
    assert agents[0]["created"] is True
    assert agents[0]["agent_id"] == "agent-1"
    assert agents[0]["subscribed"] == "subscribed"
    assert counters == {"create": 1, "subscribe": 1}

    # Persisted graph carries the agent_id on the call node.
    g = client.get("/workflows/reportzen-trial-to-paid").json()
    call_node = next(n for n in g["nodes"] if n["type"] == "call")
    assert call_node["agent_id"] == "agent-1"


def test_redeploy_is_idempotent_and_resubscribes(monkeypatch):
    counters = _fake_ringg(monkeypatch)
    g = client.get("/workflows/templates/reportzen-trial-to-paid").json()
    for n in g["nodes"]:
        if n["type"] == "call":
            n["agent_id"] = "existing-1"  # already deployed

    resp = client.post("/workflows/deploy", json={"graph": g})
    agents = resp.json()["deployment"]["agents"]
    assert agents[0]["agent_id"] == "existing-1"
    assert agents[0]["created"] is False
    assert counters["create"] == 0  # did NOT create again
    assert counters["subscribe"] == 1  # but did re-subscribe


def test_deploy_rejects_invalid_graph():
    bad = {
        "id": "x",
        "name": "x",
        "entry": "c",
        "nodes": [{"id": "c", "type": "call", "outcomes": ["yes"]}],
        "edges": [{"source": "c", "target": "ghost", "on": "yes"}],
    }
    resp = client.post("/workflows/deploy", json={"graph": bad})
    assert resp.status_code == 400
