# Zukii — Tools available (Ringg agent toolbox)

Two kinds of tools: **(A) custom tools we built** for Zukii, and **(B) Ringg's built-in tools**
you can enable on any agent. Tool data below was read live from agent
`435a1535-3d88-490d-8d39-95708123c307` (Day-before Follow-up).

---

## A. Custom Zukii tools (built by us)

### A1. Mid-call On-Call API tools (`tool_type: API_TOOL`, phase `on_call`)
The agent calls these **during** the conversation. Currently live on the Day-before agent; paste
configs from `ZUKII_ONCALL_TOOLS.md` to add to other agents (dashboard-only — no API to bulk-add).

| Tool name | Hits | Does |
|---|---|---|
| `send_checkout_link` | `n8n /zukii-postcall` | Email + WhatsApp + Telegram the upgrade link (activated/distracted) |
| `send_forwardable_summary` | `n8n /zukii-postcall` | Forwardable summary for the decision-maker (stakeholder loop) |
| `escalate_stuck_wall` ⚠️ saved as `scalate_stuck_wall` | `n8n /zukii-escalate` | Instant 🚨 Telegram alert to support with the named wall |
| `save_call_memory` | `n8n /zukii-memory-write` | Upsert outcome to `zukii_memory` so the next call is recognised |
| `send_pdf_summary` | `n8n /zukii-pdf` | Generate a PDF call summary, deliver to Telegram |
| `ping_team_telegram` | `Telegram Bot API` | Simple text ping to the team chat (guaranteed-working demo tool) |

### A2. Post-call automation (no per-agent tool needed — webhook-based, ON by default)
All Zukii agents are subscribed to `all_processing_completed` → `n8n /zukii-postcall`. After **every**
call this auto-fires the branch actions (email/WhatsApp/Telegram) + memory write-back. This is the
"tools by default for all agents" layer.

### A3. Supporting n8n workflows (the engines behind the tools)
| Workflow | ID | Trigger |
|---|---|---|
| Post-Call Actions | `QiCm25mBhambOpnz` | webhook `/zukii-postcall` |
| Memory Writeback | `I0KtKjKV1uFHY65m` | webhook `/zukii-memory-write` |
| Place-Call with Memory | `4LKarbHtVYOjVKXc` | webhook `/zukii-place-call` |
| Day-11 Trigger | `xfG8JCfBWgPzqDue` | daily 10:00 |
| Day-before Follow-up | `KH7bqnfAPQlzv92t` | daily 09:00 |
| Stuck-Wall Escalation | `3wnZGseIXiswIaJb` | webhook `/zukii-escalate` |
| Wall Weekly Digest | `SRRSPco8nrk4kLMO` | weekly Mon 09:00 |
| PDF Summary | `h9kl24Wv3UnZYpH9` | webhook `/zukii-pdf` |

---

## B. Ringg built-in tools (enable per agent in the dashboard)

### B1. On-call control tools (`tool_category: call_tool`, phase `on_call`)
Available on every telephony agent — toggle on when needed.

| Tool | `tool_type` | What it does |
|---|---|---|
| `dtmf_output` | `DTMF_TOOL` | Sends DTMF tones (0-9, *, #) — navigate IVRs, enter codes/extensions |
| `call_transfer` | `CALL_TRANSFER_TOOL` | Warm/cold transfer the live call to a human or another number |
| `wait_for_dtmf` | `WAIT_FOR_DTMF_TOOL` | Pause and wait for the caller to key in digits |
| `collect_long_input` | `COLLECT_LONG_INPUT_TOOL` | Capture a long spoken input (address, long ID) reliably |
| `stay_on_line` | `STAY_ON_LINE_TOOL` | Hold the line / keep the call alive during a wait |
| `end_call` | `END_CALL_TOOL` | Gracefully end the call |
| `<your API tools>` | `API_TOOL` | Custom On-Call API calls (section A1) |

### B2. Pre-call tools (`phase: pre_call`)
Run **before** the call connects to enrich context.

| Tool | `tool_type` | What it does |
|---|---|---|
| `greetings` | `pre_call_api_tool` | Calls `…/external_hook/time_ist_to_greetings` → time-appropriate greeting (good morning/afternoon). Currently attached to the Day-before agent. |

### B3. Post-call tools (`phase: post_call`)
Run **after** the call.

| Tool | `tool_type` | What it does |
|---|---|---|
| `callback_schedule` | `CALLBACK_SCHEDULE_TOOL` | Detects callback intent and schedules a callback (currently `is_enabled: false` — turn on for the `callback` branch) |

### B4. Embedded / web-call tools (`tool_category: embeded_tool`, channel `webcall`)
Only for the embedded web widget (not phone calls).

| Tool | `tool_type` | What it does |
|---|---|---|
| `calendar_invite` | `CALENDER_WIDGET_TOOL` | Show an inline calendar to book a slot |
| `execute_dom_action` | `DOM_ACTION_TOOL` | Dispatch DOM actions on the host page during a web conversation |
| `form_widget` | `FORM_WIDGET_TOOL` | Render an inline form to collect fields |
| `quick_reply` | `QUICK_REPLY_TOOL` | Show tappable quick-reply buttons |

---

## Notes
- **API write limit:** Ringg's On-Call API tools and Custom Analysis are **dashboard-only** —
  `PATCH /agent/v1` rejects tool writes (`edit_api_settings` → 422). Built-in tools (B1–B4) are also
  toggled in the dashboard. The post-call webhook (A2) *is* settable via API and is the bulk default.
- **Tool reuse:** saved On-Call tools carry stable `tool_id`s, so the dashboard can attach an existing
  tool to another assistant without recreating it.
- **Reference IDs:** Diagnose agent `b4e56724-…`, Day-before `435a1535-…`, Trial Concierge `c4650dfe-…`,
  KB `590fa008-…`, memory table `xMx0kIUGRo2bXikR`, Telegram chat `959767592`.
