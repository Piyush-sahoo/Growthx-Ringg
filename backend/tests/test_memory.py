"""S5: three-layer memory + memory-carrying follow-up call."""

from fastapi.testclient import TestClient

from app import memory
from app.main import app
from app.models import CallRecord

client = TestClient(app)


def test_memory_module_three_layers_and_compile():
    c = memory.new_contact(
        "+919000000001", "Asha", {"days_left": "3", "accounts_connected": "3", "reports_sent": "2"}
    )
    # rules layer present
    assert "never" in c.rules

    rec = CallRecord(
        customer_name="Asha",
        phone_number="+919000000001",
        outcome="stuck_wall",
        analysis={
            "wall_description": "Meta OAuth permission fail",
            "last_promise": "retry by Friday",
            "extension_granted": True,
            "extension_days": 3,
        },
    )
    memory.record_outcome(c, rec)  # before layer write-back
    assert len(c.before) == 1
    assert c.before[0]["wall"] == "Meta OAuth permission fail"

    cv = memory.compile_memory(c, days_left_override="1")
    assert cv["last_call_outcome"] == "stuck_wall"
    assert cv["last_promise"] == "retry by Friday"
    assert "Meta OAuth" in cv["memory_summary"]
    assert cv["days_left"] == "1"


def test_followup_call_carries_prior_wall_and_promise():
    payload = {
        "event_type": "all_processing_completed",
        "call_id": "mem-call-1",
        "client_analysis": {
            "outcome": "stuck_wall",
            "wall_description": "Meta OAuth permission fail",
            "last_promise": "retry by Friday",
            "extension_granted": True,
            "extension_days": 3,
        },
        "custom_args_values": {
            "customer_name": "Asha",
            "phone_number": "+919812340000",
            "days_left": "3",
            "accounts_connected": "3",
            "reports_sent": "2",
        },
    }
    resp = client.post("/webhooks/ringg", json=payload)
    assert resp.status_code == 200
    assert any(a.get("status") == "followup_scheduled" for a in resp.json()["actions"])

    calls = client.get("/calls").json()
    followup = next(c for c in calls if c["is_followup"])
    cv = followup["custom_args_values"]
    assert cv["last_promise"] == "retry by Friday"
    assert "Meta OAuth" in cv["memory_summary"]
    assert cv["last_call_outcome"] == "stuck_wall"
    assert cv["days_left"] == "1"  # day-before-deadline
    assert followup["parent_call_id"]  # linked to the first call


def test_no_followup_without_extension():
    payload = {
        "event_type": "all_processing_completed",
        "call_id": "mem-call-2",
        "client_analysis": {"outcome": "tourist"},
        "custom_args_values": {"customer_name": "Bo", "phone_number": "+919812341111"},
    }
    client.post("/webhooks/ringg", json=payload)
    calls = client.get("/calls").json()
    assert not any(c["is_followup"] for c in calls)
