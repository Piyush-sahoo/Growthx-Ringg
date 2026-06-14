"""Branch engine — graph-driven execution (S3).

After a call completes, resolve the outcome (Gemini fallback if Ringg's structured
outcome is missing), then traverse the workflow graph from the call node: follow
the outcome edge, fire any tool nodes, and stop at a terminal or the next call node.
"""

from __future__ import annotations

from . import llm, memory, render, tools
from .graph import NodeType, WorkflowGraph, next_target
from .models import CallRecord, CallStatus
from .store import store
from .templates import REPORTZEN_BRANCHES, REPORTZEN_GRAPH, REPORTZEN_RECALL_NODE


def _upgrade_link(record: CallRecord) -> str:
    cav = record.custom_args_values or {}
    return cav.get("upgrade_link") or cav.get("retry_link") or "https://app.reportzen.example/upgrade"


def _graph_for(record: CallRecord) -> WorkflowGraph:
    # S3 ships one template; S8 lets a run reference any workflow by id.
    return REPORTZEN_GRAPH


async def ensure_outcome(record: CallRecord) -> str | None:
    """Use the captured outcome; if absent, classify the transcript with Gemini
    against the *current call node's* allowed outcomes (not always the check-in set)."""
    if record.outcome:
        return record.outcome
    g = _graph_for(record)
    node = g.node(record.current_node_id or g.entry)
    allowed = node.outcomes if (node and node.outcomes) else REPORTZEN_BRANCHES
    if record.transcript:
        try:
            classified = llm.classify_outcome(record.transcript, allowed)
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

    if kind == "video":
        # HyperFrames personalized recap, delivered by email. Garnish / off the
        # live critical path — just another tool node.
        if tools.video_configured():
            to = cav.get("email") or "delivered@resend.dev"
            html_recap = render.build_recap_html(cav)
            try:
                res = await tools.send_recap_video(to=to, html=html_recap)
                actions.append(
                    {"tool": "video", "status": "sent", "to": to, "id": res.get("id")}
                )
            except tools.ToolError as exc:
                actions.append({"tool": "video", "status": "error", "error": str(exc)})
        else:
            actions.append({"tool": "video", "status": "skipped", "reason": "not_configured"})

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
    next_call_node: str | None = None
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
            # The workflow routes to another call — queue it (after memory write-back).
            next_call_node = tnode.id
            record.current_node_id = tnode.id
            target_id = None

    # Memory write-back (S5): update the contact's history from this call.
    contact = await _touch_contact(record)
    memory.record_outcome(contact, record)
    await store.save_contact(contact)

    # Queue a memory-carrying follow-up for the next call (every use-case: recall,
    # decision-maker, win-back). Placed on demand via POST /calls/{id}/dispatch —
    # not auto-dialed, since real timing is deferred (day-before / post-lapse).
    if next_call_node:
        followup_id = await _queue_followup(record, contact, next_call_node)
        actions.append(
            {
                "tool": "none",
                "status": "followup_scheduled",
                "call_id": followup_id,
                "node": next_call_node,
            }
        )

    record.actions = (record.actions or []) + actions
    return actions


async def _touch_contact(record: CallRecord):
    """Load (or create) the contact and refresh `now` with this call's trial fields."""
    cav = record.custom_args_values or {}
    contact = await store.get_contact(record.phone_number)
    if contact is None:
        contact = memory.new_contact(
            record.phone_number, record.customer_name, memory.now_from(cav)
        )
    else:
        contact.now.update(memory.now_from(cav))
    return contact


async def _queue_followup(record: CallRecord, contact, node_id: str) -> str:
    """Create a queued, memory-carrying follow-up call for the next call node.

    Not placed here — dispatched on demand (POST /calls/{id}/dispatch) so calls
    aren't fired back-to-back. The recall carries day-before timing; others keep
    the contact's days_left.
    """
    days_override = "1" if node_id == REPORTZEN_RECALL_NODE else None
    variables = memory.compile_memory(contact, days_left_override=days_override)
    followup = CallRecord(
        customer_name=record.customer_name,
        phone_number=record.phone_number,
        custom_args_values=variables,
        is_followup=True,
        parent_call_id=record.id,
        workflow_id=record.workflow_id or REPORTZEN_GRAPH.id,
        current_node_id=node_id,
        status=CallStatus.queued,
    )
    await store.add(followup)
    return followup.id
