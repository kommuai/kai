# Chatwoot Agent Bot integration

Kai can receive WhatsApp (and other channel) messages directly from Chatwoot **Agent Bot** webhooks and post replies back via the Chatwoot API—replacing an n8n relay.

## Flow

1. Customer sends message in Chatwoot (WhatsApp inbox).
2. Chatwoot Agent Bot `POST`s `message_created` to Kai: `/webhooks/chatwoot`.
3. Kai maps payload → `phone_number`, `content`, `conversation_id`.
4. Same pipeline as `POST /v2/agent/message`: `pre_router` → support runtime → `finalize_reply`.
5. Kai posts outgoing message to the conversation via Chatwoot Messages API.

`POST /v2/agent/message` remains available for smoke tests and rollback.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `KAI_CHATWOOT_BOT_ENABLED` | Yes (for webhook) | Set `1` to enable `/webhooks/chatwoot` |
| `KAI_CHATWOOT_API_BASE` | Yes | e.g. `https://app.chatwoot.com` |
| `KAI_CHATWOOT_API_TOKEN` | Yes | Account API access token |
| `KAI_CHATWOOT_ACCOUNT_ID` | Yes | Numeric account id |
| `KAI_CHATWOOT_WEBHOOK_SECRET` | Recommended | Shared secret; send as `X-Chatwoot-Bot-Token` header or `?token=` query |
| `KAI_CHATWOOT_INBOX_IDS` | Optional | Comma-separated inbox ids (allowlist) |
| `KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER` | Optional | `1` toggles Chatwoot conversation on LA keyword and runtime escalation |

## Chatwoot setup

1. **Settings → Agent Bots** → create or edit bot.
2. **Outgoing URL:** `https://<your-kai-host>/webhooks/chatwoot`
3. If using a secret, configure the same value in Chatwoot (header/query per your Chatwoot version) and set `KAI_CHATWOOT_WEBHOOK_SECRET`.
4. Attach the bot to the WhatsApp inbox used for Kommu support.

## Cutover from n8n

1. Deploy Kai with webhook env vars; keep n8n workflow **disabled** first.
2. Point Agent Bot Outgoing URL to Kai; set `KAI_CHATWOOT_BOT_ENABLED=1`.
3. Smoke: normal question, `LA`, `resume`, one escalation case.
4. Confirm a single bot reply per user message (idempotency on `message.id`).
5. Disable n8n workflow permanently after 24h stable.

## Rollback

1. Set `KAI_CHATWOOT_BOT_ENABLED=0` (webhook returns 503).
2. Re-enable n8n workflow and point Agent Bot URL back to n8n (or detach bot).
3. Use `POST /v2/agent/message` for manual testing if needed.

## Session keys

Phone numbers are normalized to `+60XXXXXXXXX` when possible (see `kai/lib/phone_identity.py`). This matches `tools/clear_chat.py` behavior for session lookup.

## Idempotency

Processed Chatwoot `message.id` values are stored in the session SQLite DB (`chatwoot_processed_messages` table) to avoid duplicate replies on webhook retries.
