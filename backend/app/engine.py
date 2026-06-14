"""Branch engine — graph-driven execution (S3).

After a call completes, resolve the outcome (Gemini fallback if Ringg's structured
outcome is missing), then traverse the workflow graph from the call node: follow
the outcome edge, fire any tool nodes, and stop at a terminal or the next call node.
"""

from __future__ import annotations

from . import llm, memory, render, ringg, tools
from .graph import NodeType, WorkflowGraph, next_target
from .models import CallRecord, CallStatus
from .store import store
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

    # Memory write-back (S5): update the contact's history from this call.
    contact = await _touch_contact(record)
    memory.record_outcome(contact, record)
    await store.save_contact(contact)

    # On a granted extension, schedule the memory-carrying follow-up call.
    analysis = record.analysis or {}
    if analysis.get("extension_granted") and not record.is_followup:
        followup_id = await _schedule_followup(record, contact)
        actions.append({"tool": "none", "status": "followup_scheduled", "call_id": followup_id})

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


async def _schedule_followup(record: CallRecord, contact) -> str:
    """Create + place a follow-up call (day-before-deadline) carrying prior memory."""
    variables = memory.compile_memory(contact, days_left_override="1")
    followup = CallRecord(
        customer_name=record.customer_name,
        phone_number=record.phone_number,
        custom_args_values=variables,
        is_followup=True,
        parent_call_id=record.id,
        workflow_id=record.workflow_id or REPORTZEN_GRAPH.id,
        current_node_id=REPORTZEN_GRAPH.entry,
    )
    await store.add(followup)
    try:
        res = await ringg.ringg_client.place_outbound_call(
            name=record.customer_name,
            phone_number=record.phone_number,
            custom_args_values=variables,
        )
        followup.ringg_call_id = (
            res.get("call_id") or res.get("id") or (res.get("data") or {}).get("call_id")
        )
        followup.status = CallStatus.in_progress
    except ringg.RinggError as exc:
        followup.status = CallStatus.queued
        followup.analysis = {"schedule_error": str(exc)}
    await store.update(followup)
    return followup.id
