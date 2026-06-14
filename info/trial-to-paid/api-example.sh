#!/usr/bin/env bash
set -euo pipefail

: "${RINGG_API_KEY:?Set RINGG_API_KEY in your environment}"
: "${RINGG_AGENT_ID:?Set RINGG_AGENT_ID in your environment}"
: "${RINGG_FROM_NUMBER_ID:?Set RINGG_FROM_NUMBER_ID in your environment}"
: "${CALLEE_PHONE_E164:?Set CALLEE_PHONE_E164 in E.164 format}"

RINGG_BASE_URL="${RINGG_BASE_URL:-https://prod-api.ringg.ai/ca/api/v0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

curl --fail-with-body --silent --show-error \
  --request GET "$RINGG_BASE_URL/workspace" \
  --header "X-API-KEY: $RINGG_API_KEY"

payload="$(
  sed \
    -e "s|\${CALLEE_PHONE_E164}|$CALLEE_PHONE_E164|g" \
    -e "s|\${RINGG_AGENT_ID}|$RINGG_AGENT_ID|g" \
    -e "s|\${RINGG_FROM_NUMBER_ID}|$RINGG_FROM_NUMBER_ID|g" \
    "$SCRIPT_DIR/sample-call-payload.json"
)"

curl --fail-with-body --silent --show-error \
  --request POST "$RINGG_BASE_URL/calling/outbound/individual" \
  --header "X-API-KEY: $RINGG_API_KEY" \
  --header "Content-Type: application/json" \
  --data "$payload"

# Prefer an all_processing_completed webhook in production. History is useful
# for manual verification and reconciliation.
curl --fail-with-body --silent --show-error \
  --request GET "$RINGG_BASE_URL/calling/history?limit=20&offset=0" \
  --header "X-API-KEY: $RINGG_API_KEY"
