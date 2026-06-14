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
