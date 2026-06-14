"""S3: workflow graph model, validation, traversal, and template endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.graph import Edge, GraphError, Node, NodeType, WorkflowGraph, next_target, validate_graph
from app.main import app
from app.templates import REPORTZEN_BRANCHES, REPORTZEN_GRAPH

client = TestClient(app)


def test_reportzen_graph_is_valid():
    validate_graph(REPORTZEN_GRAPH)  # should not raise
    entry = REPORTZEN_GRAPH.node(REPORTZEN_GRAPH.entry)
    assert entry.type == NodeType.call
    assert set(entry.outcomes) == set(REPORTZEN_BRANCHES)


def test_traversal_follows_outcome_edges():
    assert next_target(REPORTZEN_GRAPH, "call_checkin", "activated_distracted") == "tool_send_link"
    assert next_target(REPORTZEN_GRAPH, "call_checkin", "tourist") == "t_tourist"
    assert next_target(REPORTZEN_GRAPH, "tool_send_link") == "t_converted"  # unconditional
    assert next_target(REPORTZEN_GRAPH, "call_checkin", "nonexistent") is None


def test_invalid_edge_outcome_rejected():
    g = WorkflowGraph(
        id="bad",
        name="bad",
        entry="c",
        nodes=[
            Node(id="c", type=NodeType.call, outcomes=["yes"]),
            Node(id="t", type=NodeType.terminal),
        ],
        edges=[Edge(source="c", target="t", on="no")],  # 'no' not in outcomes
    )
    with pytest.raises(GraphError):
        validate_graph(g)


def test_dangling_edge_rejected():
    g = WorkflowGraph(
        id="bad2",
        name="bad2",
        entry="c",
        nodes=[Node(id="c", type=NodeType.call, outcomes=["yes"])],
        edges=[Edge(source="c", target="ghost", on="yes")],
    )
    with pytest.raises(GraphError):
        validate_graph(g)


def test_terminal_with_outgoing_edge_rejected():
    g = WorkflowGraph(
        id="bad3",
        name="bad3",
        entry="c",
        nodes=[
            Node(id="c", type=NodeType.call, outcomes=["yes"]),
            Node(id="t", type=NodeType.terminal),
        ],
        edges=[
            Edge(source="c", target="t", on="yes"),
            Edge(source="t", target="c"),  # terminal must not have outgoing edges
        ],
    )
    with pytest.raises(GraphError):
        validate_graph(g)


def test_template_endpoints():
    listing = client.get("/workflows/templates").json()
    assert any(t["id"] == "reportzen-trial-to-paid" for t in listing)

    g = client.get("/workflows/templates/reportzen-trial-to-paid").json()
    assert g["entry"] == "call_checkin"
    assert len(g["nodes"]) == len(REPORTZEN_GRAPH.nodes)

    assert client.get("/workflows/templates/nope").status_code == 404
