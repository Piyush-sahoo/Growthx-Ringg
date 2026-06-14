"""Flow-selection tests — verify every branch routes to the right next step.

Check-in (entry) routing is driven through the webhook; the other call nodes
(recall / decision-maker / win-back) are driven through the engine directly.
"""

from fastapi.testclient import TestClient

from app import engine
from app.main import app
from app.models import CallRecord
from app.store import store

client = TestClient(app)


def _post(outcome: str, call_id: str | None = None, extra: dict | None = None) -> dict:
    body = {
        "event_type": "all_processing_completed",
        "call_id": call_id or f"flow-{outcome}",
        "client_analysis": {"outcome": outcome, **(extra or {})},
        "custom_args_values": {"customer_name": "Asha", "phone_number": f"+9100{outcome[:3]}"},
    }
    return client.post("/webhooks/ringg", json=body).json()


def _statuses(resp: dict) -> list[tuple]:
    return [(a.get("tool"), a.get("status"), a.get("node")) for a in resp["actions"]]


# ---- Check-in (entry call) routing ----

def test_activated_distracted_sends_links_then_converts():
    s = _statuses(_post("activated_distracted"))
    assert ("email", "sent", None) in s
    assert ("whatsapp", "sent", None) in s
    assert ("none", "terminal", "t_converted") in s
    assert not any(st == "followup_scheduled" for _, st, _ in s)


def test_stakeholder_loop_queues_decision_maker_call():
    s = _statuses(_post("stakeholder_loop"))
    assert ("email", "sent", None) in s  # forwardable summary
    assert any(st == "followup_scheduled" and n == "call_stakeholder" for _, st, n in s)


def test_stuck_wall_books_fix_and_queues_recall():
    s = _statuses(_post("stuck_wall"))
    assert ("email", "sent", None) in s  # fix booking
    assert any(st == "followup_scheduled" and n == "call_recall" for _, st, n in s)


def test_price_fit_terminates():
    s = _statuses(_post("price_fit"))
    assert any(n == "t_price" for _, _, n in s)
    assert not any(st == "followup_scheduled" for _, st, _ in s)


def test_tourist_terminates_clean():
    s = _statuses(_post("tourist"))
    assert any(n == "t_tourist" for _, _, n in s)
    assert not any(st == "followup_scheduled" for _, st, _ in s)


def test_callback_queues_recall():
    s = _statuses(_post("callback"))
    assert any(st == "followup_scheduled" and n == "call_recall" for _, st, n in s)


# ---- Non-entry call routing (recall / decision-maker / win-back) ----

async def _run_node(outcome: str, node: str):
    rec = CallRecord(customer_name="A", phone_number="+91x", outcome=outcome, current_node_id=node)
    await store.add(rec)
    acts = await engine.run_branch(rec)
    return acts, rec.current_node_id


async def test_recall_converted_terminates():
    _, end = await _run_node("converted", "call_recall")
    assert end == "t_converted"


async def test_recall_no_answer_routes_to_winback():
    acts, _ = await _run_node("no_answer", "call_recall")
    assert any(
        a.get("node") == "call_winback" and a.get("status") == "followup_scheduled" for a in acts
    )


async def test_stakeholder_declined_is_lost():
    _, end = await _run_node("declined", "call_stakeholder")
    assert end == "t_lost"


async def test_stakeholder_needs_more_routes_to_recall():
    acts, _ = await _run_node("needs_more", "call_stakeholder")
    assert any(a.get("node") == "call_recall" for a in acts)


async def test_winback_reactivated_converts():
    _, end = await _run_node("reactivated", "call_winback")
    assert end == "t_converted"


# ---- Dispatching a queued follow-up actually places it ----

def test_dispatch_places_queued_followup():
    _post("stuck_wall", call_id="disp-seed")
    followups = [c for c in client.get("/calls").json() if c["is_followup"]]
    assert followups and followups[0]["status"] == "queued"

    resp = client.post(f"/calls/{followups[0]['id']}/dispatch")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["ringg_call_id"]
