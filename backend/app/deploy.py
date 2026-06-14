"""Deploy a workflow graph onto Ringg (S4).

For each call node: create a Ringg assistant (`POST /public/agent/`) and subscribe
its webhooks to our callback. If create-agent is unavailable for the workspace
(e.g. KYC-gated), fall back to the configured default assistant (A-lite) so the
workflow still has a working agent_id. Assistants are created at deploy time only.
"""

from __future__ import annotations

from . import ringg
from .config import get_settings
from .graph import NodeType, WorkflowGraph

DEFAULT_EVENTS = ["call_started", "call_completed", "all_processing_completed"]


def _agent_payload(node, graph: WorkflowGraph, voice_id: str, settings) -> dict:
    p = node.prompt or {}
    name = (p.get("agent_name") or node.label or graph.name)[:100]
    variables = sorted({"customer_name", "days_left", "upgrade_link", *(p.get("variables") or [])})
    return {
        "agent_name": name,
        "introduction_and_objective": (
            p.get("introduction_and_objective")
            or "You are ReportZen's trial concierge. Diagnose whether the trial user is "
            "activated-but-distracted, silently stuck, or just a tourist, and give the "
            "honest next step."
        )[:2000],
        "response_guidelines": (
            p.get("response_guidelines")
            or "Be honest and concise. Never invent urgency on top of the real deadline. "
            "No discount reflex. Answer data-retention questions factually."
        )[:3000],
        "task": (
            p.get("task")
            or "Call trial users in their final 72 hours, diagnose the blocker, fix or route it, "
            "and confirm the next step."
        )[:1500],
        "primary_language": settings.agent_primary_language,
        "secondary_language": settings.agent_secondary_language,
        "voice_id": voice_id,
        "intro_message": (p.get("intro_message") or "Hi, the agent from ReportZen.")[:500],
        "agent_type": "outbound",
        "custom_variables": variables,
    }


async def deploy_workflow(graph: WorkflowGraph) -> dict:
    """Create/attach a Ringg assistant per call node and subscribe webhooks.

    Mutates the graph (sets node.agent_id) and returns a per-node deploy summary.
    """
    settings = get_settings()
    callback = settings.webhook_callback_url
    voice_id = settings.agent_voice_id or await ringg.ringg_client.resolve_voice_id(
        settings.agent_primary_language
    )

    results: list[dict] = []
    for node in graph.nodes:
        if node.type != NodeType.call:
            continue

        created = reused = False
        create_error = None
        agent_id = node.agent_id  # idempotent: keep an already-deployed agent

        if not agent_id:
            try:
                agent_id = await ringg.ringg_client.create_agent(
                    _agent_payload(node, graph, voice_id, settings)
                )
                created = True
            except ringg.RinggError as exc:
                create_error = str(exc)
                # A-lite fallback: reuse the configured default assistant.
                agent_id = settings.ringg_assistant_id or None
                reused = agent_id is not None

        node.agent_id = agent_id

        subscribed = None
        if agent_id:
            try:
                await ringg.ringg_client.subscribe_webhooks(
                    agent_id=agent_id,
                    callback_url=callback,
                    event_types=DEFAULT_EVENTS,
                    secret=settings.ringg_webhook_secret,
                )
                subscribed = "subscribed"
            except ringg.RinggError as exc:
                subscribed = f"error: {exc}"

        results.append(
            {
                "node": node.id,
                "agent_id": agent_id,
                "created": created,
                "reused": reused,
                "subscribed": subscribed,
                "create_error": create_error,
            }
        )

    return {"workflow_id": graph.id, "callback_url": callback, "agents": results}
