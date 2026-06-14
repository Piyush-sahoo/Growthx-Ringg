"""Branch engine — graph-driven execution (S3).

After a call completes, resolve the outcome (Gemini fallback if Ringg's structured
outcome is missing), then traverse the workflow graph from the call node: follow
the outcome edge, fire any tool nodes, and stop at a terminal or the next call node.
"""

from __future__ import annotations

from . import llm, tools
from .graph import NodeType, WorkflowGraph, next_target
from .models import CallRecord
from .templates import REPORTZEN_BRANCHES, REPORTZEN_GRAPH


def _upgrade_link(record: CallRecord) -> str:
    cav = record.custom_args_values or {}
    return cav.get("upgrade_link") or cav.get("retry_link") or "https://app.reportzen.example/upgrade"


def _graph_for(record: CallRecord) -> WorkflowGraph:
    # S3 ships one template; S8 lets a run reference any workflow by id.
    return REPORTZEN_GRAPH


async def ensure_outcome(record: CallRecord) -> str | None:
    """Use the captured outcome; if absent, classify the transcript with Gemini."""
    if record.outcome:
        return record.outcome
    if record.transcript:
        try:
            classified = llm.classify_outcome(record.transcript, REPORTZEN_BRANCHES)
        except llm.LLMError:
            classified = None
        if classified:
            record.outcome = classified
    return record.outcome


async def _run_tool_node(record: CallRecord, node) -> list[dict]:
    """Execute a tool node. `checkout_link` sends both email + whatsapp."""
    actions: list[dict] = []
    kind = node.tool
    link = _upgrade_link(record)
    cav = record.custom_args_values or {}
    subject = node.params.get("subject") or f"{record.customer_name}, your upgrade link"
    html = node.params.get("html") or (
        f'<p>Hi {record.customer_name}, here is your link: <a href="{link}">{link}</a></p>'
    )

    if kind in ("checkout_link", "email"):
        if tools.email_configured():
            to = cav.get("email") or "delivered@resend.dev"
            try:
                res = await tools.send_email(to=to, subject=subject, html=html)
                if kind == "checkout_link":
                    record.checkout_link_sent = True
                actions.append({"tool": "email", "status": "sent", "to": to, "id": res.get("id")})
            except tools.ToolError as exc:
                actions.append({"tool": "email", "status": "error", "error": str(exc)})
        else:
            actions.append({"tool": "email", "status": "skipped", "reason": "not_configured"})

    if kind in ("checkout_link", "whatsapp"):
        if tools.whatsapp_configured():
            try:
                res = await tools.send_whatsapp(
                    to=record.phone_number,
                    body=f"Hi {record.customer_name}, your upgrade link: {link}",
                )
                if kind == "checkout_link":
                    record.checkout_link_sent = True
                actions.append({"tool": "whatsapp", "status": "sent", "id": res.get("sid")})
            except tools.ToolError as exc:
                actions.append({"tool": "whatsapp", "status": "error", "error": str(exc)})
        else:
            actions.append({"tool": "whatsapp", "status": "skipped", "reason": "not_configured"})

    return actions


async def run_branch(record: CallRecord) -> list[dict]:
    """Traverse the workflow graph from the just-completed call node."""
    g = _graph_for(record)
    record.workflow_id = g.id
    node_id = record.current_node_id or g.entry
    node = g.node(node_id)
    actions: list[dict] = []

    if node is None or node.type != NodeType.call:
        return actions

    target_id = next_target(g, node_id, record.outcome)
    while target_id:
        tnode = g.node(target_id)
        if tnode is None:
            break
        if tnode.type == NodeType.tool:
            actions += await _run_tool_node(record, tnode)
            target_id = next_target(g, tnode.id)
        elif tnode.type == NodeType.terminal:
            actions.append({"tool": "none", "status": "terminal", "node": tnode.id})
            record.current_node_id = tnode.id
            target_id = None
        elif tnode.type == NodeType.call:
            # Next call in the workflow; placed by the runner in S4/S5.
            actions.append({"tool": "none", "status": "call_queued", "node": tnode.id})
            record.current_node_id = tnode.id
            target_id = None

    record.actions = (record.actions or []) + actions
    return actions
