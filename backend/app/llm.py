"""Gemini (google-genai) helper — structured branch classification fallback.

Used when Ringg's custom-analysis `outcome` is missing/ambiguous (S2). Returns a
branch from the allowed set, or None if Gemini is not configured or unsure.
"""

from __future__ import annotations

from .config import get_settings


class LLMError(RuntimeError):
    pass


def configured() -> bool:
    return bool(get_settings().gemini_api_key)


def classify_outcome(transcript: str, allowed: list[str]) -> str | None:
    """Classify a call transcript into one of `allowed` outcomes via Gemini.

    Returns the chosen outcome string, or None if not configured / not in the set.
    """
    settings = get_settings()
    if not settings.gemini_api_key or not transcript:
        return None

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    schema = {
        "type": "object",
        "properties": {"outcome": {"type": "string", "enum": allowed}},
        "required": ["outcome"],
    }
    prompt = (
        "You classify the outcome of a sales/support phone call into exactly one "
        f"label from this set: {allowed}.\n\nTranscript:\n{transcript}\n\n"
        "Return JSON with a single key 'outcome'."
    )
    resp = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    import json

    try:
        outcome = json.loads(resp.text).get("outcome")
    except (ValueError, AttributeError) as exc:  # malformed response
        raise LLMError(f"Gemini returned unparseable output: {resp.text!r}") from exc
    return outcome if outcome in allowed else None


def _minimal_graph(prompt: str) -> dict:
    """A valid 1-call -> 1-terminal fallback graph."""
    return {
        "id": "generated-workflow",
        "name": "Generated workflow",
        "entry": "call_main",
        "nodes": [
            {
                "id": "call_main",
                "type": "call",
                "label": "Outbound call",
                "outcomes": ["done"],
                "prompt": {"agent_name": "FlowForge Agent", "intro_message": prompt[:200]},
            },
            {"id": "t_done", "type": "terminal", "label": "Done"},
        ],
        "edges": [{"source": "call_main", "target": "t_done", "on": "done"}],
    }


# JSON schema describing the WorkflowGraph shape for Gemini structured output.
# Mirrors app/graph.py (Node/Edge/WorkflowGraph).
_GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "entry": {"type": "string"},
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["call", "tool", "terminal"]},
                    "label": {"type": "string"},
                    "outcomes": {"type": "array", "items": {"type": "string"}},
                    "tool": {"type": "string"},
                },
                "required": ["id", "type"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "on": {"type": "string"},
                },
                "required": ["source", "target"],
            },
        },
    },
    "required": ["id", "name", "entry", "nodes", "edges"],
}

_GRAPH_SYSTEM_INSTRUCTION = (
    "You design voice-call workflows as a directed graph of typed nodes for an "
    "outbound calling system. Output JSON matching the provided schema.\n\n"
    "Node types:\n"
    "- 'call': places a phone call. Its 'outcomes' is the list of possible call "
    "results (short snake_case labels). A call node MUST have exactly one outgoing "
    "edge per outcome, and every outgoing edge's 'on' MUST equal one of the node's "
    "'outcomes'. Give it a 'label' and may include a 'prompt' object with "
    "'agent_name' and 'intro_message'.\n"
    "- 'tool': fires a side effect. Set 'tool' to one of 'checkout_link', 'email', "
    "'whatsapp', or 'video'. A tool node has exactly ONE outgoing edge with NO 'on' "
    "label (unconditional).\n"
    "- 'terminal': an end state. It has NO outgoing edges and NO 'tool'/'outcomes'.\n\n"
    "Rules: 'entry' must be the id of a call node. Every edge source/target must be "
    "an existing node id. Use unique node ids. Prefer concise, realistic outcome "
    "labels. The graph must be self-consistent and acyclic-ish (terminals end "
    "branches)."
)


def generate_workflow(prompt: str, base: dict | None = None) -> dict:
    """Generate a WorkflowGraph dict for a voice-call workflow described by `prompt`.

    Uses Gemini structured JSON output. If Gemini is unconfigured or returns
    something unusable, returns `base` (when given) or a minimal valid graph.
    """
    settings = get_settings()
    fallback = base if base is not None else _minimal_graph(prompt)
    if not settings.gemini_api_key or not prompt:
        return fallback

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    contents = f"Build a voice-call workflow for this goal:\n\n{prompt}"
    if base is not None:
        import json as _json

        contents += (
            "\n\nUse this existing workflow as a starting point and adapt it:\n"
            + _json.dumps(base)
        )
    try:
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_GRAPH_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=_GRAPH_SCHEMA,
            ),
        )
    except Exception:  # noqa: BLE001 — any SDK/network error falls back
        return fallback

    import json

    try:
        data = json.loads(resp.text)
    except (ValueError, AttributeError):
        return fallback
    if not isinstance(data, dict) or not data.get("nodes") or not data.get("edges"):
        return fallback
    return data
