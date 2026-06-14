"""Behavioral tests for the backend API (external services faked at the boundary)."""

from fastapi.testclient import TestClient

from app import ringg as ringg_module
from app.main import app

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "service" in resp.json()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "ringg_configured" in body


def test_history_starts_empty():
    assert client.get("/calls").json() == []


def test_webhook_string_transcript_creates_record():
    payload = {
        "event_type": "call_completed",
        "call_id": "ringg-string-1",
        "transcript": "Hello, this is a test call.",
        "custom_args_values": {"customer_name": "Test User", "phone_number": "+910000000000"},
    }
    resp = client.post("/webhooks/ringg", json=payload)
    assert resp.status_code == 200 and resp.json()["ok"] is True

    calls = client.get("/calls").json()
    assert any(c["transcript"] == "Hello, this is a test call." for c in calls)
    rec = next(c for c in calls if c["ringg_call_id"] == "ringg-string-1")
    assert rec["status"] == "completed"


def test_webhook_array_transcript_and_outcome():
    payload = {
        "event_type": "all_processing_completed",
        "call_id": "ringg-array-1",
        "transcript": [
            {"bot": "Hi Asha, your trial wraps up in two days. How has it gone?"},
            {"user": "I love it, I just haven't gotten to it."},
        ],
        "client_analysis": {"outcome": "activated_distracted", "plan_fit": "Studio"},
        "custom_args_values": {"customer_name": "Asha", "phone_number": "+919812345678"},
    }
    resp = client.post("/webhooks/ringg", json=payload)
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "activated_distracted"

    rec = next(c for c in client.get("/calls").json() if c["ringg_call_id"] == "ringg-array-1")
    assert "bot: Hi Asha" in rec["transcript"]
    assert "user: I love it" in rec["transcript"]
    assert rec["transcript_turns"] and len(rec["transcript_turns"]) == 2
    assert rec["outcome"] == "activated_distracted"
    assert rec["status"] == "completed"


def test_webhook_dedupe_on_call_id_and_event_type():
    payload = {
        "event_type": "all_processing_completed",
        "call_id": "ringg-dupe-1",
        "transcript": [{"user": "first"}],
        "custom_args_values": {"customer_name": "Dee", "phone_number": "+911234500000"},
    }
    first = client.post("/webhooks/ringg", json=payload)
    assert first.json().get("deduped") is not True

    # Same call_id + event_type → deduped, no second record created.
    second = client.post("/webhooks/ringg", json={**payload, "transcript": [{"user": "second"}]})
    assert second.json().get("deduped") is True

    matching = [c for c in client.get("/calls").json() if c["ringg_call_id"] == "ringg-dupe-1"]
    assert len(matching) == 1
    assert "first" in matching[0]["transcript"]  # second event was ignored


def test_create_call_success_with_faked_ringg(monkeypatch):
    async def _fake_place(**kwargs):
        assert kwargs["name"] == "Asha Rao"
        assert kwargs["phone_number"] == "+919812345678"
        return {"call_id": "ringg-created-1"}

    monkeypatch.setattr(ringg_module.ringg_client, "place_outbound_call", _fake_place)
    resp = client.post(
        "/calls",
        json={"customer_name": "Asha Rao", "phone_number": "+919812345678"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["ringg_call_id"] == "ringg-created-1"


def test_create_call_upstream_error_returns_502(monkeypatch):
    async def _fake_err(**kwargs):
        raise ringg_module.RinggError("Ringg API 500: boom")

    monkeypatch.setattr(ringg_module.ringg_client, "place_outbound_call", _fake_err)
    resp = client.post(
        "/calls",
        json={"customer_name": "Boom", "phone_number": "+911111111111"},
    )
    assert resp.status_code == 502
    # The failed call is still recorded.
    assert any(c["status"] == "failed" for c in client.get("/calls").json())
