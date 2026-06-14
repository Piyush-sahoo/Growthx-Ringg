---
name: Ringg
description: Use when building voice agent integrations, making outbound calls, running bulk campaigns, managing phone numbers, configuring webhooks, or retrieving call analytics and transcripts. Reach for this skill when a user needs to automate phone-based interactions, integrate voice calling into a backend system, or manage AI-powered conversations at scale.
metadata:
    mintlify-proj: ringg
    version: "1.0"
---

# Ringg AI Skill

## Product Summary

Ringg AI is an AI voice agent platform that automates phone-based interactions at scale. Agents use it to make outbound calls, run bulk campaigns, receive inbound calls, embed voice widgets on websites, and retrieve post-call analytics. The platform is controlled via REST API (`https://prod-api.ringg.ai/ca/api/v0`), dashboard UI, or webhooks. Key resources are **Assistants** (voice agents), **Numbers** (caller IDs), **Campaigns** (bulk calling), and **Webhooks** (real-time events). Authenticate all API requests with `X-API-KEY` header. See https://docs.ringg.ai for the full documentation.

---

## When to Use

Reach for this skill when:

- **Making individual calls**: A user action should trigger one outbound call via API (`POST /calling/outbound/individual`).
- **Running bulk campaigns**: Upload a CSV contact list and schedule calls to many recipients with one assistant.
- **Setting up webhooks**: Configure real-time event delivery for call state, transcripts, recordings, and analysis.
- **Managing phone numbers**: Buy, import, or assign caller IDs for outbound and inbound flows.
- **Retrieving call data**: Query call history, transcripts, recordings, and analytics for dashboards or reconciliation.
- **Configuring assistants**: Create or update voice agents with prompts, voices, knowledge bases, and custom variables.
- **Integrating with external systems**: Connect Ringg to CRMs, data warehouses, or support tools via API or webhooks.

---

## Quick Reference

### API Base URL and Authentication

```bash
export RINGG_BASE_URL="https://prod-api.ringg.ai/ca/api/v0"
export RINGG_API_KEY="your-api-key"

# All requests require X-API-KEY header
curl --header "X-API-KEY: $RINGG_API_KEY" "$RINGG_BASE_URL/workspace"
```

### Core IDs to Store

| ID | Source | Used For |
|---|---|---|
| `agent_id` | `GET /agent/all` or dashboard | Individual calls, campaigns, webhooks |
| `from_number_id` | `GET /workspace/numbers` | Outbound calls (preferred over `from_number`) |
| `call_id` | Call initiation response | Webhook dedupe, history lookup, support |
| `bulk_list_id` | Campaign CSV upload | Campaign start, status, history, analytics |

### Essential Endpoints

| Task | Endpoint | Method |
|---|---|---|
| Verify API key | `/workspace` | GET |
| List assistants | `/agent/all` | GET |
| Get workspace numbers | `/workspace/numbers` | GET |
| Make one call | `/calling/outbound/individual` | POST |
| Get call history | `/calling/history` | GET |
| Get call details | `/calling/history/{call_id}` | GET |
| Upload campaign CSV | `/campaign/upload-contact-list` | POST |
| Start campaign | `/campaign/start` | POST |
| Configure webhooks | `/agent/v1` (operation: `edit_event_subscriptions`) | PATCH |

### Phone Number Format

Always use E.164 format with country code:
```
+919876543210  ✓ Correct
919876543210   ✗ Missing country code
+91 9876543210 ✗ Spaces not allowed
```

### Custom Variables in Prompts

Reference dynamic data in assistant prompts using `@{{variable_name}}`:
```
"prompt": "Hello @{{callee_name}}, this is a reminder about your order @{{order_id}}"

// Pass values via custom_args_values
"custom_args_values": {
  "callee_name": "John",
  "order_id": "ORD-1042"
}
```

---

## Decision Guidance

### When to Use Individual Calls vs Campaigns

| Scenario | Use Individual Call API | Use Campaign |
|---|---|---|
| One user action triggers one call | ✓ | |
| Calling 100+ contacts on a schedule | | ✓ |
| Transactional calls (order confirmation, appointment reminder) | ✓ | |
| Bulk outreach (lead qualification, collections) | | ✓ |
| Need to pass dynamic data per call | ✓ | ✓ (via CSV) |
| Need to control concurrency across campaigns | | ✓ |

### When to Use Webhook Events vs History Polling

| Scenario | Use Webhooks | Use History API |
|---|---|---|
| Real-time UI updates | ✓ | |
| Production integrations with external systems | ✓ | |
| Dashboard or reporting (batch processing) | | ✓ |
| Need full transcript and analysis immediately | ✓ (`all_processing_completed`) | |
| Reconciliation or debugging | | ✓ |
| Avoid polling overhead | ✓ | |

### When to Use `from_number_id` vs `from_number`

| Scenario | Use `from_number_id` | Use `from_number` |
|---|---|---|
| Number is stable in your workspace | ✓ | |
| Number formatting may change | ✓ | |
| Legacy integration or dynamic number | | ✓ |
| **Always prefer** | ✓ | |

**Important**: Provide exactly one — never both `from_number_id` and `from_number`.

### Knowledge Base Type: Deterministic vs Non-Deterministic

| Scenario | Deterministic KB | Non-Deterministic KB |
|---|---|---|
| Pricing tables, policy fields, structured data | ✓ | |
| FAQs, articles, general documents | | ✓ |
| Need exact field retrieval | ✓ | |
| Faster setup, less configuration | | ✓ |
| Predictable answers | ✓ | |

---

## Workflow

### Making Your First Outbound Call

1. **Verify authentication**: Call `GET /workspace` to confirm API key and check available credits.
2. **Select an assistant**: Call `GET /agent/all` and choose an assistant configured for outbound calls. Save the `agent_id`.
3. **Select a caller number**: Call `GET /workspace/numbers` and choose a number. Save the `from_number_id`.
4. **Prepare recipient data**: Format the phone number in E.164 format (e.g., `+919876543210`). Identify any custom variables your prompt uses.
5. **Initiate the call**: Call `POST /calling/outbound/individual` with recipient, assistant, number, and custom variables.
6. **Store the call ID**: Save the returned `call_id` for webhook matching and history lookup.
7. **Receive results**: Configure webhooks for `all_processing_completed` to get transcript, recording, and analysis, or poll `GET /calling/history` for manual verification.

### Running a Bulk Campaign

1. **Prepare the CSV**: Create a file with `phone_number` column and any columns matching assistant custom variables (e.g., `callee_name`, `order_id`).
2. **Verify assistant and numbers**: Confirm the assistant is configured for outbound calls and at least one number is available.
3. **Upload the CSV**: Call `POST /campaign/upload-contact-list` with the file. Save the returned `bulk_list_id`.
4. **Configure campaign settings**: Specify campaign name, assistant, numbers, start/end times, and timezone.
5. **Start the campaign**: Call `POST /campaign/start` with the `bulk_list_id` and settings.
6. **Monitor progress**: Use `GET /campaign/all` to check status, or configure webhooks to receive call events.
7. **Retrieve results**: Use `GET /calling/history` filtered by `bulk_list_id` for transcripts and outcomes.

### Setting Up Webhooks

1. **Choose events**: Decide which events your system needs: `call_started`, `call_completed`, `recording_completed`, `platform_analysis_completed`, `client_analysis_completed`, or `all_processing_completed`.
2. **Prepare endpoint**: Create an HTTPS endpoint that accepts POST requests, validates the event, stores it idempotently, and returns `2xx` quickly.
3. **Configure subscription**: Call `PATCH /agent/v1` with `operation: "edit_event_subscriptions"`, providing the assistant ID, event types, callback URL, and optional auth headers.
4. **Dedupe events**: Use `call_id` + `event_type` as the primary dedupe key to handle retries.
5. **Process asynchronously**: Return `2xx` immediately, then process the event in your own job queue.

---

## Common Gotchas

- **API key in client code**: Never expose `X-API-KEY` in browser or mobile source code. Keep it server-side only. The web widget uses a managed flow that does not require the key.
- **Both `from_number_id` and `from_number` provided**: The API rejects requests with both fields. Provide exactly one.
- **Phone number format**: Missing country code or spaces in the number causes validation errors. Always use E.164 format.
- **Custom variable mismatch**: If your prompt references `@{{callee_name}}` but `custom_args_values` does not include `callee_name`, the assistant will not speak the value. Check prompt placeholders match the keys you pass.
- **Webhook endpoint not returning `2xx`**: Ringg retries failed webhooks. If your endpoint returns `4xx` or `5xx`, events may be lost or delayed. Always return `2xx` after validating the request.
- **Recording URL expiration**: Recording URLs are valid for 24 hours only. Download and store recordings within that window if you need to retain them.
- **Campaign CSV headers with spaces**: Column names like `callee name` (with space) will not match prompt variables like `@{{callee_name}}`. Use underscores or camelCase.
- **Calling window timezone mismatch**: If `call_start_time` is `09:00` and timezone is `Asia/Kolkata` but the recipient is in a different timezone, calls may not go out when expected. Confirm timezone matches your audience.
- **Insufficient credits**: Calls fail silently if the workspace has no credits. Check `GET /workspace` response for `credits` before initiating calls.
- **Deprecated endpoint**: `POST /calling/outbound/individual` is stable but newer integrations should consider `POST /calling/outbound/individual/v2` for number pool management.

---

## Verification Checklist

Before submitting work with Ringg AI:

- [ ] API key is stored in a server-side secret manager, not in code or logs.
- [ ] Phone numbers are in E.164 format with country code (e.g., `+919876543210`).
- [ ] Custom variable keys in `custom_args_values` match prompt placeholders (e.g., `@{{callee_name}}`).
- [ ] Exactly one of `from_number_id` or `from_number` is provided, never both.
- [ ] Assistant is configured for the correct call direction (outbound, inbound, or webcall).
- [ ] Workspace has sufficient credits for the call volume.
- [ ] Webhook endpoint returns `2xx` immediately and processes events asynchronously.
- [ ] Webhook dedupe logic uses `call_id` + `event_type` as the primary key.
- [ ] Campaign CSV headers match assistant custom variable names.
- [ ] Call start/end times and timezone are appropriate for the recipient audience.
- [ ] Recording URLs are downloaded within 24 hours if retention is required.
- [ ] Call IDs are stored in the database for history lookup and support debugging.

---

## Resources

- **Comprehensive page listing**: https://docs.ringg.ai/llms.txt — Use this for full navigation of all endpoints and guides.
- **Quick Start Guide**: https://docs.ringg.ai/api-reference/quick-start/guide — Step-by-step walkthrough from API key to first call.
- **Webhook Setup**: https://docs.ringg.ai/webhooks/initial-setup — Configure real-time event subscriptions and endpoint requirements.
- **Security Guidelines**: https://docs.ringg.ai/get-started/best-practices/security-guidelines — API key management, data protection, and compliance.

---

> For additional documentation and navigation, see: https://docs.ringg.ai/llms.txt