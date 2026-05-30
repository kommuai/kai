# Kai WhatsApp Bridge (Baileys)

Sidecar for **QR linking** (Studio onboarding) and **multi-tenant message worker** (inbound → Kai → WhatsApp reply).

## Run locally

```bash
cd studio/whatsapp-bridge
npm install
export KAI_TENANTS_ROOT=/home/ting/workspace   # parent of kai-tenant-* dirs
export KAI_REPO=/home/ting/workspace/kai
npm start
```

Listens on `http://127.0.0.1:18791` by default (`WHATSAPP_BRIDGE_PORT`).

Studio backend uses `WHATSAPP_BRIDGE_URL` (default `http://127.0.0.1:18791`).

**Note:** Do not use port 8091 on this machine — it is often taken by nginx/Cursor bridge.

## What runs in one process

| Component | Role |
|-----------|------|
| HTTP API (`/v1/link/*`) | QR pairing during new-tenant wizard |
| HTTP API (`POST /v1/worker/send`) | Studio human-agent replies → WhatsApp DM |
| Worker manager | Scans `KAI_TENANTS_ROOT` every 15s for `whatsapp_baileys` tenants |

When a new tenant is created (or `workspace.yaml` / auth creds change), the worker **starts automatically** on the next scan — no manual restart.

During QR linking, the worker **pauses** that tenant’s auth directory so only the link socket is active.

## Tenant requirements

Under `kai-tenant-<slug>/`:

- `workspace.yaml` → `channels.inbound.provider: whatsapp_baileys` and `channels.whatsapp_baileys.enabled: true`
- `data/whatsapp/baileys-auth/creds.json` (from Studio QR flow)

## Environment

| Variable | Default |
|----------|---------|
| `KAI_TENANTS_ROOT` | `~/workspace` |
| `KAI_REPO` | `studio/whatsapp-bridge/../..` |
| `KAI_PYTHON` | `python3` |
| `WHATSAPP_BRIDGE_PORT` | `18791` |
| `WHATSAPP_WORKER_SCAN_MS` | `15000` |
| `WHATSAPP_WORKER_ENABLED` | `1` (set `0` to disable worker, link API only) |
| `WHATSAPP_REPLY_HUMANIZE` | `1` — inbound bot replies use antiban pacing (gaussian delay + WPM typing) |
| `WHATSAPP_REPLY_DELAY_MIN_MS` | `2000` — rate-limiter / gaussian delay floor |
| `WHATSAPP_REPLY_DELAY_MAX_MS` | `60000` — rate-limiter / gaussian delay ceiling |
| `WA_ANTIBAN_TYPING_MAX_MS` | `10000` — cap WPM typing simulation duration per reply |
| `WHATSAPP_STUDIO_ANTIBAN_DELAY` | `0` — Studio manual sends skip antiban delay (still respect pause/timelock) |
| `WA_ANTIBAN_AUTO_PAUSE_AT` | `high` — auto-pause all outbound when health risk reaches this level |
| `WA_ANTIBAN_TIMEZONE` | `Asia/Kuala_Lumpur` — circadian typing rhythm |
| `WA_ANTIBAN_STEALTH_RAMP` | `1` — delayed `available` presence after connect |
| `WA_ANTIBAN_RECONNECT_RAMP_MS` | `60000` — post-reconnect send throttle ramp |
| `WA_ANTIBAN_BAD_MAC_THRESHOLD` | `3` — session degraded → auto-pause |

## Health

`GET /health` → `{ ok: true, worker: { tenants: [...], ... } }`

## Inbound path

WhatsApp message → `kai_inbound.py` (`KAI_HOME` = tenant workspace) → `support_runtime` → reply sent via Baileys. Sessions appear in Studio **Inbox** (`data/sessions.db`).

### Anti-ban (`baileys-antiban`)

Per-tenant guard (`tenant-guard.mjs`) wraps each worker with:

- **Gaussian send delays** + **WPM typing** (`composing` / `paused` cycles) on inbound bot replies
- **Health monitor** with **auto-pause** at high/critical risk (no outbound until resumed)
- **Session health** (Bad MAC tracking) → auto-pause on degradation
- **LID/PN canonicalization** on outbound JIDs
- **Typed disconnect backoff** + **post-reconnect throttle**
- **Stealth connect** (random browser fingerprint, delayed online ramp)
- Persisted warm-up state: `data/whatsapp/antiban-state.json` under each tenant home

## systemd (Phase B)

```bash
cd ../deploy/systemd-user && ./install.sh
systemctl --user enable --now kai-whatsapp-bridge.service
```

See `studio/README.md` for Studio UI status badges.
