"""Smoke tests for the backend API."""

from fastapi.testclient import TestClient

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


def test_calls_empty_then_webhook_creates_record():
    # History starts empty.
    assert client.get("/calls").status_code == 200

    # An inbound webhook for an unknown call creates a record.
    payload = {
        "event": "call_completed",
        "call_id": "ringg-test-123",
        "transcript": "Hello, this is a test call.",
        "custom_args_values": {"customer_name": "Test User", "phone_number": "+910000000000"},
    }
    resp = client.post("/webhooks/ringg", json=payload)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    calls = client.get("/calls").json()
    assert any(c["transcript"] == "Hello, this is a test call." for c in calls)


def test_create_call_without_ringg_key_returns_502():
    payload = {"customer_name": "Asha", "phone_number": "+911111111111"}
    resp = client.post("/calls", json=payload)
    # No RINGG_API_KEY configured in test env -> upstream error surfaced as 502.
    assert resp.status_code == 502
