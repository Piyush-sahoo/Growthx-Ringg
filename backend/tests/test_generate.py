"""S9: workflow generation endpoint — behavioral (Gemini faked) + live."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.graph import WorkflowGraph, validate_graph
from app.main import app

client = TestClient(app)
settings = get_settings()


def _valid_graph_dict() -> dict:
    return {
        "id": "gen-test",
        "name": "Payment failed recovery",
        "entry": "call_dunning",
        "nodes": [
            {
                "id": "call_dunning",
                "type": "call",
                "label": "Payment-failed call",
                "outcomes": ["will_pay", "churn"],
            },
            {"id": "tool_link", "type": "tool", "label": "Send pay link", "tool": "checkout_link"},
            {"id": "t_paid", "type": "terminal", "label": "Paying"},
            {"id": "t_churn", "type": "terminal", "label": "Churned"},
        ],
        "edges": [
            {"source": "call_dunning", "target": "tool_link", "on": "will_pay"},
            {"source": "call_dunning", "target": "t_churn", "on": "churn"},
            {"source": "tool_link", "target": "t_paid"},
        ],
    }


def test_generate_returns_valid_graph(monkeypatch):
    monkeypatch.setattr("app.llm.generate_workflow", lambda prompt, base: _valid_graph_dict())
    resp = client.post("/workflows/generate", json={"prompt": "call failed payments"})
    assert resp.status_code == 200
    graph_dict = resp.json()["graph"]

    g = WorkflowGraph.model_validate(graph_dict)
    validate_graph(g)  # must not raise
    assert g.entry == "call_dunning"
    assert any(n.type.value == "call" for n in g.nodes)
    assert {n.id for n in g.nodes} == {"call_dunning", "tool_link", "t_paid", "t_churn"}


def test_generate_falls_back_to_base_when_invalid(monkeypatch):
    """An invalid generated graph falls back to the valid base template."""
    bad = {
        "id": "bad",
        "name": "broken",
        "entry": "nope",  # entry not in nodes -> validate_graph fails
        "nodes": [{"id": "x", "type": "terminal"}],
        "edges": [],
    }
    monkeypatch.setattr("app.llm.generate_workflow", lambda prompt, base: bad)
    resp = client.post(
        "/workflows/generate",
        json={"prompt": "whatever", "base_template_id": "reportzen-trial-to-paid"},
    )
    assert resp.status_code == 200
    g = WorkflowGraph.model_validate(resp.json()["graph"])
    validate_graph(g)
    assert g.id == "reportzen-trial-to-paid"


def test_generate_rejects_invalid_without_base(monkeypatch):
    """No base + unusable generation -> 422."""
    bad = {
        "id": "bad",
        "name": "broken",
        "entry": "nope",
        "nodes": [{"id": "x", "type": "terminal"}],
        "edges": [],
    }
    monkeypatch.setattr("app.llm.generate_workflow", lambda prompt, base: bad)
    resp = client.post("/workflows/generate", json={"prompt": "whatever"})
    assert resp.status_code == 422


def test_generate_unknown_base_template_404():
    resp = client.post(
        "/workflows/generate", json={"prompt": "x", "base_template_id": "does-not-exist"}
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.skipif(not settings.gemini_api_key, reason="GEMINI_API_KEY not set")
def test_generate_live():
    """The real endpoint produces a valid graph with at least one call node."""
    resp = client.post(
        "/workflows/generate",
        json={
            "prompt": (
                "call customers whose payment failed; if they want to pay send a "
                "link, else mark churn"
            )
        },
    )
    assert resp.status_code == 200
    g = WorkflowGraph.model_validate(resp.json()["graph"])
    validate_graph(g)
    assert sum(1 for n in g.nodes if n.type.value == "call") >= 1
