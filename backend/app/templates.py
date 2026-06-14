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
        Node(
            id="tool_book_fix",
            type=NodeType.tool,
            label="Book the wall-fix + extend",
            tool="email",
            params={"kind": "fix_booking"},
        ),
        # Call 2 — the decision-maker / co-founder call (stakeholder use-case).
        Node(
            id="call_stakeholder",
            type=NodeType.call,
            label="Decision-maker call",
            outcomes=["approved", "declined", "needs_more"],
            prompt={
                "agent_name": "ReportZen — Decision-maker",
                "intro_message": (
                    "Hi @{{decision_owner}}, Riya from ReportZen. @{{callee_name}} has been "
                    "trialing our client-reporting tool and asked me to walk you through "
                    "the plan in two minutes — is now okay?"
                ),
            },
        ),
        # Call 3 — the memory-carrying day-before-deadline recall use-case.
        Node(
            id="call_recall",
            type=NodeType.call,
            label="Day-before recall",
            outcomes=["converted", "still_stuck", "no_answer"],
            prompt={
                "agent_name": "ReportZen — Recall",
                "intro_message": (
                    "Hi @{{callee_name}}, Riya from ReportZen again. Last time "
                    "@{{last_promise}} — your trial ends tomorrow, so I wanted to close "
                    "the loop. Did that get sorted?"
                ),
            },
        ),
        # Call 4 — post-lapse win-back use-case (trial already expired).
        Node(
            id="call_winback",
            type=NodeType.call,
            label="Post-lapse win-back",
            outcomes=["reactivated", "not_interested"],
            prompt={
                "agent_name": "ReportZen — Win-back",
                "intro_message": (
                    "Hi @{{callee_name}}, Riya from ReportZen. Your trial lapsed but your "
                    "@{{accounts_connected}} connected accounts and reports are still saved "
                    "for a few more days — want me to switch you back on?"
                ),
            },
        ),
        Node(id="t_converted", type=NodeType.terminal, label="Converted"),
        Node(id="t_price", type=NodeType.terminal, label="Price-fit sized"),
        Node(id="t_tourist", type=NodeType.terminal, label="Closed clean"),
        Node(id="t_stuck", type=NodeType.terminal, label="Still stuck — escalated"),
        Node(id="t_lost", type=NodeType.terminal, label="Lost / not interested"),
    ],
    edges=[
        Edge(source="call_checkin", target="tool_send_link", on="activated_distracted"),
        Edge(source="call_checkin", target="tool_send_summary", on="stakeholder_loop"),
        Edge(source="call_checkin", target="tool_book_fix", on="stuck_wall"),
        Edge(source="call_checkin", target="t_price", on="price_fit"),
        Edge(source="call_checkin", target="t_tourist", on="tourist"),
        Edge(source="call_checkin", target="call_recall", on="callback"),
        Edge(source="tool_send_link", target="t_converted"),
        Edge(source="tool_send_summary", target="call_stakeholder"),
        Edge(source="tool_book_fix", target="call_recall"),
        Edge(source="call_stakeholder", target="tool_send_link", on="approved"),
        Edge(source="call_stakeholder", target="t_lost", on="declined"),
        Edge(source="call_stakeholder", target="call_recall", on="needs_more"),
        Edge(source="call_recall", target="t_converted", on="converted"),
        Edge(source="call_recall", target="t_stuck", on="still_stuck"),
        Edge(source="call_recall", target="call_winback", on="no_answer"),
        Edge(source="call_winback", target="t_converted", on="reactivated"),
        Edge(source="call_winback", target="t_lost", on="not_interested"),
    ],
)

# The graph node id of the memory-carrying recall call.
REPORTZEN_RECALL_NODE = "call_recall"

_TEMPLATES = {REPORTZEN_GRAPH.id: REPORTZEN_GRAPH}


def list_templates() -> list[dict]:
    return [{"id": g.id, "name": g.name} for g in _TEMPLATES.values()]


def get_template(template_id: str) -> WorkflowGraph | None:
    return _TEMPLATES.get(template_id)
