"""S11: HyperFrames recap video tool — behavioral (Resend faked) + live."""

import pytest

from app import engine, render, tools
from app.config import get_settings
from app.graph import Edge, Node, NodeType, WorkflowGraph, validate_graph
from app.models import CallRecord

settings = get_settings()


def _video_graph() -> WorkflowGraph:
    g = WorkflowGraph(
        id="recap-test",
        name="Recap test",
        entry="call_checkin",
        nodes=[
            Node(
                id="call_checkin",
                type=NodeType.call,
                label="Check-in",
                outcomes=["happy"],
            ),
            Node(id="tool_video", type=NodeType.tool, label="Send recap", tool="video"),
            Node(id="t_done", type=NodeType.terminal, label="Done"),
        ],
        edges=[
            Edge(source="call_checkin", target="tool_video", on="happy"),
            Edge(source="tool_video", target="t_done"),
        ],
    )
    validate_graph(g)  # the custom graph itself must be valid
    return g


def test_build_recap_html_contains_customer_name():
    html = render.build_recap_html(
        {
            "customer_name": "Asha Rao",
            "accounts_connected": "3",
            "reports_sent": "12",
            "plan_fit": "Growth",
            "upgrade_link": "https://app.x/up/asha",
        }
    )
    assert html
    assert "Asha Rao" in html
    assert "data-composition" in html
    assert "https://app.x/up/asha" in html


def test_video_node_records_sent_action(monkeypatch):
    """Driving a call -> tool(video) -> terminal graph records a sent video action."""
    g = _video_graph()
    monkeypatch.setattr(engine, "_graph_for", lambda record: g)
    # Make the test independent of whether RESEND is configured in the env.
    monkeypatch.setattr(tools, "video_configured", lambda: True)

    record = CallRecord(
        customer_name="Asha",
        phone_number="+919812345678",
        custom_args_values={
            "customer_name": "Asha",
            "email": "delivered@resend.dev",
            "accounts_connected": "3",
            "reports_sent": "12",
            "plan_fit": "Growth",
        },
        outcome="happy",
        current_node_id="call_checkin",
    )

    import asyncio

    actions = asyncio.run(engine.run_branch(record))
    video_actions = [a for a in actions if a.get("tool") == "video"]
    assert len(video_actions) == 1
    assert video_actions[0]["status"] == "sent"
    assert video_actions[0]["id"] == "fake-video"
    assert any(a.get("status") == "terminal" for a in actions)


@pytest.mark.integration
@pytest.mark.skipif(not settings.resend_api_key, reason="RESEND_API_KEY not set")
async def test_recap_video_send_live():
    """Resend really accepts the recap email and returns an id."""
    html = render.build_recap_html({"customer_name": "Live Test", "plan_fit": "Pro"})
    res = await tools.send_recap_video(to="delivered@resend.dev", html=html)
    assert res.get("id")
