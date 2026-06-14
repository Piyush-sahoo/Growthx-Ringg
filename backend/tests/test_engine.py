"""S2: branch engine — deterministic routing + tool firing (tools faked)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _completion(call_id, outcome=None, transcript=None, cav=None):
    body = {
        "event_type": "all_processing_completed",
        "call_id": call_id,
        "custom_args_values": cav or {"customer_name": "Asha", "phone_number": "+919812345678"},
    }
    if outcome is not None:
        body["client_analysis"] = {"outcome": outcome}
    if transcript is not None:
        body["transcript"] = transcript
    return body


def test_activated_distracted_sends_checkout_link():
    resp = client.post(
        "/webhooks/ringg",
        json=_completion(
            "br-1",
            outcome="activated_distracted",
            cav={
                "customer_name": "Asha",
                "phone_number": "+919812345678",
                "upgrade_link": "https://app.x/up/asha",
            },
        ),
    )
    assert resp.status_code == 200
    actions = resp.json()["actions"]
    assert any(a["tool"] == "email" and a["status"] == "sent" for a in actions)

    rec = next(c for c in client.get("/calls").json() if c["ringg_call_id"] == "br-1")
    assert rec["outcome"] == "activated_distracted"
    assert rec["checkout_link_sent"] is True


def test_tourist_branch_is_noop():
    resp = client.post("/webhooks/ringg", json=_completion("br-2", outcome="tourist"))
    actions = resp.json()["actions"]
    assert all(a["tool"] != "email" or a["status"] != "sent" for a in actions)

    rec = next(c for c in client.get("/calls").json() if c["ringg_call_id"] == "br-2")
    assert rec["outcome"] == "tourist"
    assert rec["checkout_link_sent"] is False


def test_llm_fallback_when_outcome_missing(monkeypatch):
    # No structured outcome → engine classifies the transcript via Gemini (stubbed).
    monkeypatch.setattr(
        "app.llm.classify_outcome", lambda transcript, allowed: "activated_distracted"
    )
    resp = client.post(
        "/webhooks/ringg",
        json=_completion(
            "br-3",
            transcript=[{"user": "I love it, just haven't gotten to it"}],
            cav={"customer_name": "Bo", "phone_number": "+910000000001", "upgrade_link": "x"},
        ),
    )
    assert resp.json()["outcome"] == "activated_distracted"
    rec = next(c for c in client.get("/calls").json() if c["ringg_call_id"] == "br-3")
    assert rec["checkout_link_sent"] is True
