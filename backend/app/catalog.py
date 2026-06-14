"""Tool catalog — the tools available across Ringg agents.

Two groups: custom tools we built for Zukii (A) and Ringg's built-in tools (B).
Read live per-agent attachment via GET /agents/{id}/tools; this is the static
"what's possible" reference shown in the app.

Note: Ringg's on-call API tools + custom analysis are dashboard-only to write
(PATCH /agent/v1 rejects tool writes). The post-call webhook is settable via API.
"""

TOOL_CATALOG = {
    "custom_oncall_api": {
        "group": "Custom Zukii tools — on-call API",
        "phase": "on_call",
        "tools": [
            {"name": "send_checkout_link", "hits": "n8n /zukii-postcall",
             "does": "Email + WhatsApp + Telegram the upgrade link (activated/distracted)"},
            {"name": "send_forwardable_summary", "hits": "n8n /zukii-postcall",
             "does": "Forwardable summary for the decision-maker (stakeholder loop)"},
            {"name": "escalate_stuck_wall", "hits": "n8n /zukii-escalate",
             "does": "Instant Telegram alert to support with the named wall"},
            {"name": "save_call_memory", "hits": "n8n /zukii-memory-write",
             "does": "Upsert outcome to zukii_memory so the next call is recognised"},
            {"name": "send_pdf_summary", "hits": "n8n /zukii-pdf",
             "does": "Generate a PDF call summary, deliver to Telegram"},
            {"name": "ping_team_telegram", "hits": "Telegram Bot API",
             "does": "Simple text ping to the team chat"},
        ],
    },
    "post_call_webhook": {
        "group": "Post-call automation (ON by default, all agents)",
        "phase": "post_call",
        "tools": [
            {"name": "all_processing_completed → n8n /zukii-postcall",
             "does": "After every call: fires branch actions (email/WhatsApp/Telegram) + "
                     "memory write-back"},
        ],
    },
    "builtin_oncall": {
        "group": "Ringg built-in — on-call control",
        "phase": "on_call",
        "tools": [
            {"name": "dtmf_output", "type": "DTMF_TOOL", "does": "Send DTMF tones (0-9, *, #)"},
            {"name": "call_transfer", "type": "CALL_TRANSFER_TOOL",
             "does": "Transfer the live call to a human"},
            {"name": "wait_for_dtmf", "type": "WAIT_FOR_DTMF_TOOL",
             "does": "Pause and wait for the caller to key in digits"},
            {"name": "collect_long_input", "type": "COLLECT_LONG_INPUT_TOOL",
             "does": "Capture a long spoken input (address, long ID)"},
            {"name": "stay_on_line", "type": "STAY_ON_LINE_TOOL",
             "does": "Hold the line during a wait"},
            {"name": "end_call", "type": "END_CALL_TOOL", "does": "Gracefully end the call"},
        ],
    },
    "builtin_precall": {
        "group": "Ringg built-in — pre-call",
        "phase": "pre_call",
        "tools": [
            {"name": "greetings", "type": "pre_call_api_tool",
             "does": "Time-appropriate greeting (good morning/afternoon) via external hook"},
        ],
    },
    "builtin_postcall": {
        "group": "Ringg built-in — post-call",
        "phase": "post_call",
        "tools": [
            {"name": "callback_schedule", "type": "CALLBACK_SCHEDULE_TOOL",
             "does": "Detect callback intent and schedule a callback"},
        ],
    },
    "builtin_embedded": {
        "group": "Ringg built-in — embedded (web widget only)",
        "phase": "embedded",
        "tools": [
            {"name": "calendar_invite", "type": "CALENDER_WIDGET_TOOL",
             "does": "Inline calendar to book a slot"},
            {"name": "execute_dom_action", "type": "DOM_ACTION_TOOL",
             "does": "Dispatch DOM actions on host page"},
            {"name": "form_widget", "type": "FORM_WIDGET_TOOL",
             "does": "Inline form to collect fields"},
            {"name": "quick_reply", "type": "QUICK_REPLY_TOOL",
             "does": "Tappable quick-reply buttons"},
        ],
    },
}
