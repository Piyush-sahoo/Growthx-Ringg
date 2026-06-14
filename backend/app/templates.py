"""Workflow templates (the "select & modify" library).

ReportZen trial-to-paid is the hardened, scored workflow. The graph below is the
canonical artifact the engine executes, the visualizer renders, and deploy pushes
to Ringg.
"""

from __future__ import annotations

from .graph import Edge, Node, NodeType, WorkflowGraph

REPORTZEN_BRANCHES = [
    "activated_distracted",
    "stakeholder_loop",
    "stuck_wall",
    "price_fit",
    "tourist",
    "callback",
]

REPORTZEN_GRAPH = WorkflowGraph(
    id="reportzen-trial-to-paid",
    name="ReportZen — Trial-to-paid (final 72h)",
    entry="call_checkin",
    nodes=[
        Node(
            id="call_checkin",
            type=NodeType.call,
            label="Final-72h check-in",
            outcomes=REPORTZEN_BRANCHES,
            prompt={
                "agent_name": "ReportZen Trial Concierge",
                "intro_message": (
                    "Hi @{{customer_name}}, the agent from ReportZen. Your trial wraps up "
                    "in @{{days_left}} days, and instead of another countdown email I "
                    "thought I'd ask: how has it actually gone?"
                ),
            },
        ),
        Node(
            id="tool_send_link",
            type=NodeType.tool,
            label="Send checkout link",
            tool="checkout_link",
        ),
        Node(
            id="tool_send_summary",
            type=NodeType.tool,
            label="Send forwardable summary",
            tool="email",
            params={"kind": "forwardable_summary"},
        ),
        Node(id="t_converted", type=NodeType.terminal, label="Converted"),
        Node(id="t_stakeholder", type=NodeType.terminal, label="Decision-maker looped"),
        Node(id="t_stuck", type=NodeType.terminal, label="Wall fixed / extended"),
        Node(id="t_price", type=NodeType.terminal, label="Price-fit sized"),
        Node(id="t_tourist", type=NodeType.terminal, label="Closed clean"),
        Node(id="t_callback", type=NodeType.terminal, label="Callback booked"),
    ],
    edges=[
        Edge(source="call_checkin", target="tool_send_link", on="activated_distracted"),
        Edge(source="call_checkin", target="tool_send_summary", on="stakeholder_loop"),
        Edge(source="call_checkin", target="t_stuck", on="stuck_wall"),
        Edge(source="call_checkin", target="t_price", on="price_fit"),
        Edge(source="call_checkin", target="t_tourist", on="tourist"),
        Edge(source="call_checkin", target="t_callback", on="callback"),
        Edge(source="tool_send_link", target="t_converted"),
        Edge(source="tool_send_summary", target="t_stakeholder"),
    ],
)

_TEMPLATES = {REPORTZEN_GRAPH.id: REPORTZEN_GRAPH}


def list_templates() -> list[dict]:
    return [{"id": g.id, "name": g.name} for g in _TEMPLATES.values()]


def get_template(template_id: str) -> WorkflowGraph | None:
    return _TEMPLATES.get(template_id)
