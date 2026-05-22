# Kai security model

## Chat API (open by design)

`POST /agent/message` and `POST /v2/agent/message` are **unauthenticated** so n8n/WhatsApp webhooks can call them without custom headers.

**Production controls (required):**

- Terminate TLS at your reverse proxy (nginx, Cloudflare, etc.).
- Restrict source IPs to n8n, Twilio, or your integration hosts.
- Rate-limit at the gateway if exposed to the public internet.

Do **not** expose the service directly on `0.0.0.0` without network controls.

## Admin API

Routes under `/admin/*` require header `x-admin-token` matching `ADMIN_TOKEN` in `.env` (constant-time compare).

- Set a long random `ADMIN_TOKEN` before production.
- Enable `KAI_STRICT_STARTUP=1` or `KAI_REQUIRE_STRONG_ADMIN_TOKEN=1` to fail boot when the token is weak.
- `/ready` reports `admin_token_weak` and marks not ready when strong token is required.

## Debug fields

Agent debug metadata (`debug_route_agent` in the JSON body) is returned only when:

1. `KAI_ROUTE_AGENT_DEBUG_ENABLED=1`, **and**
2. The request includes a valid `x-admin-token`.

Otherwise debug is omitted even if the client sends `debug_route_agent`.

## Service API

`POST /v2/agent/query` and `/v2/agent/search` require `KAI_SERVICE_KEYS` (see `kai/core/authz/service_auth.py`).

## Secrets

- Store secrets only in `.env` or mounted files under `./secrets` (Docker).
- Never commit `.env` or service account JSON.
- Plugins run as subprocesses (`03_tools/plugins/*/main.py`) with the same OS user as the API — treat plugin code as trusted tenant content.

## Media

Static files under `/media` are mounted only when `KAI_MEDIA_PUBLIC=1`. Leave unset in production unless you intend public media URLs.

## Plugins

Visitor-pass and other plugins may use tenant credentials (`SMARTSERVA_*`, etc.) from environment variables configured per deployment.
