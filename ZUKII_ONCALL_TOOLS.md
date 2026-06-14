# Zukii — Ringg On-Call API tools (paste-ready)

These are **mid-call tools** (Ringg "On-Call API"). The voice agent calls them **during** the
conversation. For each tool below, in the Ringg modal set:

- **Name** → the `Name` field (top box)
- **Method** → the `POST` dropdown
- **api_url** → the URL box
- **Headers** tab → click **Add Row**, add each header `key : value`
- **Body** tab → switch to **raw / JSON** and paste the JSON block
- Then **Test API** → **Add to assistant**

All n8n webhooks below are **public, no auth**. Header `Content-Type: application/json` on every tool.

> ## ⚠️ CRITICAL — how to fill the Body (read this first)
> Ringg's Body editor treats **`@` as "insert a variable."** So:
> - **NEVER hardcode a value containing `@`** (like an email) — the editor turns `@gmail.com` into a
>   broken variable chip → *"Invalid JSON"* and *"Source 'x' is not available."*
> - For any value that comes from the call, **type `@` → pick source `custom_args` → the variable**.
>   It becomes a chip. The agent's custom variables (callee_name, mobile_number, user_email,
>   upgrade_link, plan_fit, days_left, last_call_outcome, …) all live under **`custom_args`**.
> - Plain fixed strings (like `"activated_distracted"`) stay as normal quoted JSON.
> - To **Test API**, put sample values in the per-variable **"test value"** boxes (an email is fine there).
> - The JSON below shows `@custom_args.X` where you should insert a variable via the picker.
> - The **curl** blocks (for terminal testing) use real literal values and are unaffected by this.

---

## 1. `send_checkout_link`  — send the upgrade link live (activated/distracted user)

| Field | Value |
|---|---|
| Name | `send_checkout_link` |
| Method | `POST` |
| api_url | `https://n8n.vobiz.ai/webhook/zukii-postcall` |
| Header | `Content-Type: application/json` |

**Body** — insert each `@custom_args.X` via the `@` picker (don't type a literal email):
```
{
  "client_analysis": { "trial_status": "activated_distracted", "plan_fit": @custom_args.plan_fit },
  "custom_args_values": {
    "callee_name": @custom_args.callee_name,
    "user_email": @custom_args.user_email,
    "mobile_number": @custom_args.mobile_number,
    "upgrade_link": @custom_args.upgrade_link
  }
}
```
**Fires:** email (Resend) + WhatsApp (Twilio) + Telegram with the checkout link.

> **For tools 2–6 below:** same rule — wherever you see `{{X}}`, instead insert `@custom_args.X`
> via the `@` picker, and leave fixed strings (like `"stuck_wall"`) as normal quoted JSON.
> Values the agent decides on the call (e.g. `wall_description`) can be inserted with `#` (dynamic value).

**Test API curl:**
```bash
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-postcall" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"activated_distracted","plan_fit":"Solo"},"custom_args_values":{"callee_name":"Piyush","user_email":"piyush.sahoo713@gmail.com","mobile_number":"+919148227303","upgrade_link":"https://zukii.app/upgrade/piyush"}}'
```

---

## 2. `send_forwardable_summary` — summary for the decision-maker (stakeholder loop)

| Field | Value |
|---|---|
| Name | `send_forwardable_summary` |
| Method | `POST` |
| api_url | `https://n8n.vobiz.ai/webhook/zukii-postcall` |
| Header | `Content-Type: application/json` |

**Body (JSON):**
```json
{
  "client_analysis": { "trial_status": "stakeholder_loop", "plan_fit": "{{plan_fit}}", "decision_owner": "{{decision_owner}}" },
  "custom_args_values": {
    "callee_name": "{{callee_name}}",
    "user_email": "{{user_email}}",
    "mobile_number": "{{mobile_number}}",
    "upgrade_link": "{{upgrade_link}}"
  }
}
```

**Test API curl:**
```bash
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-postcall" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"stakeholder_loop","plan_fit":"Solo","decision_owner":"co-founder"},"custom_args_values":{"callee_name":"Piyush","user_email":"piyush.sahoo713@gmail.com","mobile_number":"+919148227303","upgrade_link":"https://zukii.app/upgrade/piyush"}}'
```

---

## 3. `escalate_stuck_wall` — alert support on Telegram (blocked user)

| Field | Value |
|---|---|
| Name | `escalate_stuck_wall` |
| Method | `POST` |
| api_url | `https://n8n.vobiz.ai/webhook/zukii-escalate` |
| Header | `Content-Type: application/json` |

**Body (JSON):**
```json
{
  "client_analysis": { "trial_status": "stuck_wall", "wall_description": "{{wall_description}}", "plan_fit": "{{plan_fit}}" },
  "custom_args_values": {
    "callee_name": "{{callee_name}}",
    "mobile_number": "{{mobile_number}}",
    "days_left": "{{days_left}}"
  }
}
```
**Fires:** instant 🚨 Telegram alert to the support chat (only when trial_status is `stuck_wall`).

**Test API curl:**
```bash
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-escalate" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"stuck_wall","wall_description":"Google Ads OAuth scope","plan_fit":"Solo"},"custom_args_values":{"callee_name":"Asha","mobile_number":"+919812345678","days_left":2}}'
```

---

## 4. `save_call_memory` — write the outcome so the NEXT call is recognised

| Field | Value |
|---|---|
| Name | `save_call_memory` |
| Method | `POST` |
| api_url | `https://n8n.vobiz.ai/webhook/zukii-memory-write` |
| Header | `Content-Type: application/json` |

**Body (JSON):**
```json
{
  "client_analysis": {
    "trial_status": "{{trial_status}}",
    "wall_description": "{{wall_description}}",
    "plan_fit": "{{plan_fit}}",
    "extension_granted": "{{extension_granted}}"
  },
  "custom_args_values": {
    "callee_name": "{{callee_name}}",
    "mobile_number": "{{mobile_number}}",
    "days_left": "{{days_left}}",
    "upgrade_link": "{{upgrade_link}}",
    "user_email": "{{user_email}}"
  }
}
```
**Writes:** upserts the `zukii_memory` table (call_count++) so the follow-up agent opens from this.

**Test API curl:**
```bash
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-memory-write" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"stuck_wall","wall_description":"CSV import failed","plan_fit":"Solo","extension_granted":true},"custom_args_values":{"callee_name":"Piyush","mobile_number":"+919148227303","days_left":3,"upgrade_link":"https://zukii.app/u/p","user_email":"piyush.sahoo713@gmail.com"}}'
```

---

## 5. `send_pdf_summary` — generate + deliver a PDF call summary (Telegram)

| Field | Value |
|---|---|
| Name | `send_pdf_summary` |
| Method | `POST` |
| api_url | `https://n8n.vobiz.ai/webhook/zukii-pdf` |
| Header | `Content-Type: application/json` |

**Body (JSON):**
```json
{
  "client_analysis": {
    "trial_status": "{{trial_status}}",
    "wall_description": "{{wall_description}}",
    "plan_fit": "{{plan_fit}}",
    "extension_granted": "{{extension_granted}}",
    "extension_days": "{{extension_days}}"
  },
  "custom_args_values": {
    "callee_name": "{{callee_name}}",
    "mobile_number": "{{mobile_number}}",
    "upgrade_link": "{{upgrade_link}}"
  }
}
```

**Test API curl:**
```bash
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-pdf" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"stuck_wall","wall_description":"CSV date-format import failed","plan_fit":"Solo","extension_granted":true,"extension_days":3},"custom_args_values":{"callee_name":"Piyush","mobile_number":"+919148227303","upgrade_link":"https://zukii.app/upgrade/piyush"}}'
```

---

## 6. `ping_team_telegram` — simplest possible tool (guaranteed to work, flat body)

Direct Telegram Bot API — no n8n in the path. Great for a demo "watch it send live" beat.

| Field | Value |
|---|---|
| Name | `ping_team_telegram` |
| Method | `POST` |
| api_url | `https://api.telegram.org/bot8990690040:AAGuF0hSgSmiy7SutUXgUGRHWsm1QJYCWBQ/sendMessage` |
| Header | `Content-Type: application/json` |

**Body (JSON):**
```json
{ "chat_id": 959767592, "text": "Zukii live update: {{callee_name}} — {{trial_status}}. Link: {{upgrade_link}}" }
```

**Test API curl:**
```bash
curl -s -X POST "https://api.telegram.org/bot8990690040:AAGuF0hSgSmiy7SutUXgUGRHWsm1QJYCWBQ/sendMessage" -H "Content-Type: application/json" -d '{"chat_id":959767592,"text":"Zukii live update: Piyush — activated_distracted. Link: https://zukii.app/upgrade/piyush"}'
```

---

## (Optional) target the local backend via ngrok instead of n8n

Live tunnel → local FastAPI backend: `https://occasionally-isoelastic-dorie.ngrok-free.dev`
(⚠️ URL changes on every ngrok restart; add header `ngrok-skip-browser-warning: 1`).

| Field | Value |
|---|---|
| api_url | `https://occasionally-isoelastic-dorie.ngrok-free.dev/webhooks/ringg` |
| Headers | `Content-Type: application/json` · `ngrok-skip-browser-warning: 1` |

---

### Reference IDs
- Diagnose agent: `b4e56724-b3fa-45bf-9744-dd55d6e780c2`
- Day-before Follow-up agent: `435a1535-3d88-490d-8d39-95708123c307`
- Knowledge Base: `590fa008-d34e-4c78-ae8d-8a0da2949aad`
- from_number_id: `ffc7dd03-3a4d-46ef-9aab-5aba0699ad36` (+912268095634)
- Telegram bot `@Eingg_bot` · chat_id `959767592`
- Memory Data Table: `xMx0kIUGRo2bXikR` (zukii_memory)

---

## FULL CURL TOOLBOX — everything literal, nothing from .env

Every command below is self-contained (key, URLs, IDs hardcoded). Paste any line and run.

### Ringg API
```bash
# Check credits / workspace
curl -s -H "X-API-KEY: 1f8260e4-a881-4888-bf46-acb631099781" "https://prod-api.ringg.ai/ca/api/v0/workspace"

# List all agents
curl -s -H "X-API-KEY: 1f8260e4-a881-4888-bf46-acb631099781" "https://prod-api.ringg.ai/ca/api/v0/agent/all"

# List caller numbers
curl -s -H "X-API-KEY: 1f8260e4-a881-4888-bf46-acb631099781" "https://prod-api.ringg.ai/ca/api/v0/workspace/numbers"

# Place a LIVE call — Day-11 Diagnose agent (first call, no memory)
curl -s -L -X POST "https://prod-api.ringg.ai/ca/api/v0/calling/outbound/individual" \
  -H "X-API-KEY: 1f8260e4-a881-4888-bf46-acb631099781" -H "Content-Type: application/json" -d '{
  "name":"Piyush","mobile_number":"+919148227303",
  "agent_id":"b4e56724-b3fa-45bf-9744-dd55d6e780c2",
  "from_number_id":"ffc7dd03-3a4d-46ef-9aab-5aba0699ad36",
  "custom_args_values":{"callee_name":"Piyush","user_email":"piyush.sahoo713@gmail.com","upgrade_link":"https://zukii.app/upgrade/piyush","days_left":"3","integrations_connected":"3","automations_run":"2","plan_fit":"Solo","last_promise":"","memory_summary":"First outreach.","last_call_outcome":"","last_call_date":""}}'

# Place a LIVE call — Day-before Follow-up agent (memory-aware, 2nd call)
curl -s -L -X POST "https://prod-api.ringg.ai/ca/api/v0/calling/outbound/individual" \
  -H "X-API-KEY: 1f8260e4-a881-4888-bf46-acb631099781" -H "Content-Type: application/json" -d '{
  "name":"Piyush","mobile_number":"+919148227303",
  "agent_id":"435a1535-3d88-490d-8d39-95708123c307",
  "from_number_id":"ffc7dd03-3a4d-46ef-9aab-5aba0699ad36",
  "custom_args_values":{"callee_name":"Piyush","user_email":"piyush.sahoo713@gmail.com","upgrade_link":"https://zukii.app/upgrade/piyush","days_left":"1","plan_fit":"Solo","last_call_outcome":"stuck_wall","last_call_date":"2026-06-14","wall":"CSV date-format import failed","last_promise":"extended 3 days to fix import","memory_summary":"Prior call: stuck on CSV import; extended 3 days."}}'

# Call history (latest 5)
curl -s -H "X-API-KEY: 1f8260e4-a881-4888-bf46-acb631099781" "https://prod-api.ringg.ai/ca/api/v0/calling/history?page=1&page_size=5"

# One call's details + analysis
curl -s -H "X-API-KEY: 1f8260e4-a881-4888-bf46-acb631099781" "https://prod-api.ringg.ai/ca/api/v0/calling/history/CALL_ID_HERE?send_analysis=true"
```

### n8n workflows (public, no auth)
```bash
# 1. Post-Call Actions (email + WhatsApp + Telegram)
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-postcall" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"activated_distracted","plan_fit":"Solo","wall_description":""},"custom_args_values":{"callee_name":"Piyush","user_email":"piyush.sahoo713@gmail.com","mobile_number":"+919148227303","upgrade_link":"https://zukii.app/upgrade/piyush"}}'

# 2. Memory Writeback (upsert; next call recognised)
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-memory-write" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"stuck_wall","wall_description":"CSV import failed","plan_fit":"Solo","extension_granted":true},"custom_args_values":{"callee_name":"Piyush","mobile_number":"+919148227303","days_left":3,"upgrade_link":"https://zukii.app/u/p","user_email":"piyush.sahoo713@gmail.com"}}'

# 3. Place-Call with Memory (dry_run:true = assemble only, no live call)
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-place-call" -H "Content-Type: application/json" -d '{"phone":"+919148227303","name":"Piyush","dry_run":true}'

# 6. Stuck-Wall Escalation (Telegram alert; only on stuck_wall)
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-escalate" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"stuck_wall","wall_description":"Google Ads OAuth scope","plan_fit":"Solo"},"custom_args_values":{"callee_name":"Asha","mobile_number":"+919812345678","days_left":2}}'

# 8. PDF Summary (generates a PDF, delivers to Telegram)
curl -s -X POST "https://n8n.vobiz.ai/webhook/zukii-pdf" -H "Content-Type: application/json" -d '{"client_analysis":{"trial_status":"stuck_wall","wall_description":"CSV date-format import failed","plan_fit":"Solo","extension_granted":true,"extension_days":3},"custom_args_values":{"callee_name":"Piyush","mobile_number":"+919148227303","upgrade_link":"https://zukii.app/upgrade/piyush"}}'
```

### Telegram (direct)
```bash
# Send a message to the team chat
curl -s -X POST "https://api.telegram.org/bot8990690040:AAGuF0hSgSmiy7SutUXgUGRHWsm1QJYCWBQ/sendMessage" -H "Content-Type: application/json" -d '{"chat_id":959767592,"text":"Zukii: test message"}'

# Confirm the bot + find chat_ids
curl -s "https://api.telegram.org/bot8990690040:AAGuF0hSgSmiy7SutUXgUGRHWsm1QJYCWBQ/getUpdates"
```

### Local backend (via ngrok)
```bash
# Health
curl -s -H "ngrok-skip-browser-warning: 1" "https://occasionally-isoelastic-dorie.ngrok-free.dev/health"

# Place a call through the backend (reads/writes memory in MongoDB/in-memory)
curl -s -X POST -H "ngrok-skip-browser-warning: 1" -H "Content-Type: application/json" \
  "https://occasionally-isoelastic-dorie.ngrok-free.dev/calls" -d '{"name":"Piyush","phone_number":"+919148227303","custom_args_values":{"callee_name":"Piyush"}}'
```
