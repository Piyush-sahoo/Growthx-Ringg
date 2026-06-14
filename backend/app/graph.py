"""Workflow graph model + validation (S3).

A workflow is a directed graph of typed nodes:
- ``call``     — places a Ringg call; its `outcomes` are the labels of its outgoing edges.
- ``tool``     — fires a side effect (email/whatsapp/checkout_link); one unconditional edge.
- ``terminal`` — an end state; no outgoing edges.

Edges leaving a call node carry ``on`` (the outcome label). This same JSON is
produced by the brainstorm (S9), rendered by the visualizer (S7), executed by the
engine, and deployed to Ringg (S4).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    call = "call"
    tool = "tool"
    terminal = "terminal"


class Node(BaseModel):
    id: str
    type: NodeType
    label: str | None = None
    # call node
    outcomes: list[str] = Field(default_factory=list)
    prompt: dict[str, Any] | None = None  # deploy-time fields for /public/agent (S4)
    agent_id: str | None = None  # set at deploy (S4)
    # tool node
    tool: str | None = None  # "checkout_link" | "email" | "whatsapp"
    params: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    source: str
    target: str
    on: str | None = None  # outcome label for edges leaving a call node


class WorkflowGraph(BaseModel):
    id: str
    name: str
    entry: str
    nodes: list[Node]
    edges: list[Edge]

    def node(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def out_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source == node_id]


class GraphError(ValueError):
    pass


def validate_graph(g: WorkflowGraph) -> None:
    """Raise GraphError if the graph is malformed."""
    ids = {n.id for n in g.nodes}
    if len(ids) != len(g.nodes):
        raise GraphError("duplicate node ids")
    if g.entry not in ids:
        raise GraphError(f"entry node '{g.entry}' is not in the graph")

    for e in g.edges:
        if e.source not in ids:
            raise GraphError(f"edge source '{e.source}' is not a node")
        if e.target not in ids:
            raise GraphError(f"edge target '{e.target}' is not a node")

    for n in g.nodes:
        outs = g.out_edges(n.id)
        if n.type == NodeType.call:
            labels = [e.on for e in outs]
            if any(label is None for label in labels):
                raise GraphError(f"call node '{n.id}' has an edge without an 'on' outcome")
            for label in labels:
                if label not in n.outcomes:
                    raise GraphError(
                        f"call node '{n.id}' has edge on '{label}' not in outcomes {n.outcomes}"
                    )
            if len(set(labels)) != len(labels):
                raise GraphError(f"call node '{n.id}' has duplicate outcome edges")
        elif n.type == NodeType.tool:
            if len(outs) > 1:
                raise GraphError(f"tool node '{n.id}' must have at most one outgoing edge")
            if any(e.on for e in outs):
                raise GraphError(f"tool node '{n.id}' edge must be unconditional (no 'on')")
        elif n.type == NodeType.terminal:
            if outs:
                raise GraphError(f"terminal node '{n.id}' must have no outgoing edges")


def next_target(g: WorkflowGraph, node_id: str, outcome: str | None = None) -> str | None:
    """Return the next node id from `node_id`, choosing by `outcome` if given."""
    outs = g.out_edges(node_id)
    if outcome is not None:
        return next((e.target for e in outs if e.on == outcome), None)
    return outs[0].target if outs else None
