#!/usr/bin/env python3
"""Create the ReportZen knowledge base on Ringg AI from the FAQ/policy docs.

============================================================================
DO NOT RUN REPEATEDLY — the Ringg "Create Knowledge Base" endpoint is
RATE-LIMITED to 10 requests per hour per workspace (see info/ringg-ai-skill.md
and PLAN.md §8). Pre-build the KB once; do not generate it per-deploy and never
loop this script on stage. A second accidental run can burn the hourly budget.
============================================================================

This is a REFERENCE script for the FlowForge S6 deliverable. It documents the
exact flow to register the ReportZen agent's knowledge base (the FAQ/policy docs
from info/reportzen-dossier.md §9) so the voice agent can answer pricing, data
retention/export, OAuth fixes, white-label setup, seat limits, and refund
questions from grounded content rather than improvising.

Auth & endpoint (from info/ringg-ai-skill.md):
  - Base URL : https://prod-api.ringg.ai/ca/api/v0   (env RINGG_BASE_URL)
  - Auth     : X-API-KEY header                       (env RINGG_API_KEY)
  - Endpoint : POST /knowledge-base   (Create Knowledge Base; 10 req/hour)
               Creates a non-deterministic KB from FAQs / files / URLs.

NOTE on request shape: per the Ringg docs the create endpoint accepts FAQ
question/answer pairs, files, and URLs. The exact field names can vary by API
version — verify against the live OpenAPI spec
(https://docs.ringg.ai/api-reference / docs.ringg.ai/llms.txt) before a real
run. This script sends a JSON body with `name` and an `faqs` list of
{question, answer} objects, which matches the documented non-deterministic FAQ
flow; adjust `_build_payload()` if your workspace's schema differs.

Usage (intentionally guarded — will NOT do anything without --confirm):
    RINGG_API_KEY=sk-... python scripts/create_knowledge_base.py --confirm
    python scripts/create_knowledge_base.py --dry-run   # print payload, no call
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

# --- Config ---------------------------------------------------------------

DEFAULT_BASE_URL = "https://prod-api.ringg.ai/ca/api/v0"
# Relative path of the Create Knowledge Base endpoint (rate-limited 10/hour).
CREATE_KB_PATH = "/knowledge-base"
KB_NAME = "ReportZen Trial-to-Paid — Agent KB"
REQUEST_TIMEOUT_SECONDS = 60


# --- Knowledge base content ----------------------------------------------
# The FAQ/policy docs the agent answers from. Mirrors info/reportzen-dossier.md
# §9. Each entry becomes one FAQ question/answer pair in the non-deterministic
# knowledge base.

FAQ_DOCS: list[dict[str, str]] = [
    {
        "question": "What does ReportZen cost and which plan fits my agency?",
        "answer": (
            "Studio is Rs 5,000/month and covers up to 5 client connections. "
            "Pro is Rs 12,000/month for agencies past 10 client connections and "
            "larger delivery teams (more seats). We size by your client-connection "
            "count and put you on the plan that fits, telling you the trigger to "
            "upgrade. Billing is monthly; ACV is about Rs 60k/year on Studio. We do "
            "not upsell beyond your needs and do not discount to close."
        ),
    },
    {
        "question": "What happens to my data if I cancel? Can I export it?",
        "answer": (
            "Your data — connected-account metrics and generated reports — is yours. "
            "You can export reports and the underlying data anytime from "
            "Settings > Data Export. If you cancel or your trial lapses, data is "
            "retained for a grace period before deletion and you can export during "
            "that window. We do not sell or share your client data. (State the exact "
            "retention window from product policy when asked; do not invent a number.)"
        ),
    },
    {
        "question": (
            "Connecting a client's Meta or Google account fails with a "
            "permission error — how do I fix it?"
        ),
        "answer": (
            "Meta: connect using the Business Manager that holds the client's ad "
            "account, as an admin; the client may need to add your agency as a "
            "Partner in their BM. Grant ALL requested permission scopes — "
            "un-ticking one breaks reporting — then re-run Connect. "
            "Google: select the correct Google account (not a personal Gmail) and "
            "accept the Google Ads / Analytics read permission prompt; ensure the "
            "agency has at least read access to the property. If access is "
            "client-side, forward this guide to the client and re-connect once they "
            "grant access."
        ),
    },
    {
        "question": "How do I set up white-label branding (logo and custom domain)?",
        "answer": (
            "Logo & colours: Settings > White-label — upload a PNG logo, set a brand "
            "colour and your agency name; the next report renders branded. "
            "Custom domain: add the provided CNAME record to your DNS, then verify "
            "in-app; reports and the client portal then serve under your domain. "
            "Result: client reports go out under your brand, not ReportZen's."
        ),
    },
    {
        "question": "I can't invite a teammate — it says I've hit the seat limit. Why?",
        "answer": (
            "The trial and Studio tier include a fixed number of seats. Inviting more "
            "teammates beyond that requires Pro. Seats map to your delivery team "
            "size and we'll size you onto the plan that fits — we don't bump seats "
            "artificially to push an upgrade."
        ),
    },
    {
        "question": "My CSV import keeps failing — what format does it expect?",
        "answer": (
            "The importer expects ISO dates (YYYY-MM-DD) and a header row matching "
            "the provided template. The most common failure is DD/MM/YYYY dates or "
            "Excel auto-reformatting dates on save. Re-save the date column as text "
            "in YYYY-MM-DD and re-upload. Download the CSV template from "
            "Settings > Import to match columns exactly."
        ),
    },
    {
        "question": "What is your refund and cancellation policy?",
        "answer": (
            "Plans are monthly with no long-term lock-in; cancel anytime and you "
            "won't be billed the next cycle. We don't run a discount-to-stay program "
            "— pricing is the same for everyone at a given plan. Refunds for "
            "accidental or duplicate charges are handled by support; routine monthly "
            "fees are not pro-rated mid-cycle. (State exact refund terms from product "
            "policy; do not invent.)"
        ),
    },
    {
        "question": "When am I actually getting value from ReportZen (activation)?",
        "answer": (
            "You're getting real value once you've connected at least 3 client "
            "accounts and sent at least 1 white-label report. Fastest path: connect "
            "your top clients, send one branded report this week, then roll out the "
            "rest."
        ),
    },
]


# --- Payload + request ----------------------------------------------------


def _build_payload() -> dict:
    """Build the Create Knowledge Base request body.

    Documented non-deterministic FAQ flow: a named KB with question/answer
    pairs. Adjust field names here if your workspace's API version differs
    (verify against docs.ringg.ai/llms.txt / the OpenAPI spec).
    """
    return {
        "name": KB_NAME,
        "type": "non_deterministic",
        "faqs": [
            {"question": doc["question"], "answer": doc["answer"]}
            for doc in FAQ_DOCS
        ],
    }


def _require_api_key() -> str:
    api_key = os.environ.get("RINGG_API_KEY", "").strip()
    if not api_key:
        sys.exit(
            "RINGG_API_KEY is not set. Export it (server-side secret) before running:\n"
            "  export RINGG_API_KEY=sk-...\n"
            "Never hard-code the key or commit it."
        )
    return api_key


def create_knowledge_base() -> dict:
    """POST the FAQ docs to the Ringg Create Knowledge Base endpoint.

    Returns the parsed JSON response (expected to contain the new
    knowledge_base id). Raises on non-2xx. Remember: 10 requests/hour limit.
    """
    api_key = _require_api_key()
    base_url = os.environ.get("RINGG_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    url = f"{base_url}{CREATE_KB_PATH}"
    payload = _build_payload()
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = client.post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Ringg create-knowledge-base failed {resp.status_code}: {resp.text}"
        )
    return resp.json()


# --- CLI ------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create the ReportZen knowledge base on Ringg AI. "
            "RATE-LIMITED 10/hour — do not run repeatedly."
        )
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required to actually call the rate-limited Create KB endpoint.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload that would be sent and exit without calling the API.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.dry_run:
        print(f"DRY RUN — would POST to {CREATE_KB_PATH} (10/hour rate limit):")
        print(json.dumps(_build_payload(), indent=2, ensure_ascii=False))
        return 0

    if not args.confirm:
        print(
            "Refusing to run without --confirm.\n"
            "The Ringg Create Knowledge Base endpoint is rate-limited to 10 "
            "requests/hour; an accidental run can exhaust the budget.\n"
            "  - Inspect the payload first:  python scripts/create_knowledge_base.py --dry-run\n"
            "  - Create for real (once):     python scripts/create_knowledge_base.py --confirm",
            file=sys.stderr,
        )
        return 2

    result = create_knowledge_base()
    print("Knowledge base created. Response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
